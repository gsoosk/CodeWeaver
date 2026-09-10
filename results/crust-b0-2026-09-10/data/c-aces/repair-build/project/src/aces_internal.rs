use crate::channel::{Channel, Parameters};
use crate::error::{AcesError, Result};
use crate::matrix::Matrix3D;
use crate::polynomial::{PolyArray, Polynomial};

use std::cell::Cell;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

#[allow(unused_imports)]
use AcesError as _AcesErrorAlias;

const EPROB: f64 = 0.5;

// ---------------------------------------------------------------------
// Minimal, self-contained pseudo-random number generator (std-only).
// ---------------------------------------------------------------------

static SEED_COUNTER: AtomicU64 = AtomicU64::new(0);

thread_local! {
    static RNG_STATE: Cell<u64> = Cell::new(seed_value());
}

fn seed_value() -> u64 {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64;
    let counter = SEED_COUNTER.fetch_add(1, Ordering::Relaxed);
    let mut seed = nanos ^ counter.wrapping_mul(0x9E37_79B9_7F4A_7C15);
    if seed == 0 {
        seed = 0x1234_5678_9ABC_DEF1;
    }
    seed
}

fn next_u64() -> u64 {
    RNG_STATE.with(|state| {
        let mut x = state.get();
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        state.set(x);
        x
    })
}

fn next_f64() -> f64 {
    ((next_u64() >> 11) as f64) / ((1u64 << 53) as f64)
}

/// Return a random value in the inclusive range [lo, hi].
fn randrange(lo: u64, hi: u64) -> u64 {
    if hi <= lo {
        return lo;
    }
    let range = hi - lo + 1;
    lo + (next_u64() % range)
}

fn clamp(lo: u64, hi: u64, val: u64) -> u64 {
    if val < lo {
        lo
    } else if val > hi {
        hi
    } else {
        val
    }
}

fn normal_rand(mean: u64, stddev: u64) -> u64 {
    if stddev == 0 {
        return mean;
    }
    let mut u1 = next_f64();
    if u1 <= 0.0 {
        u1 = 1e-12;
    }
    let u2 = next_f64();
    let z0 = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();
    let val = mean as f64 + stddev as f64 * z0;
    if val < 0.0 {
        0
    } else {
        val.round() as u64
    }
}

// ---------------------------------------------------------------------
// Polynomial helpers (local, mirroring the semantics of the original
// Polynomial.c routines which are not part of this translation unit).
// ---------------------------------------------------------------------

fn new_poly(size: usize) -> Polynomial {
    Polynomial {
        coeffs: vec![0i64; size],
        size,
    }
}

fn set_zero(p: &mut Polynomial) {
    for c in p.coeffs.iter_mut() {
        *c = 0;
    }
}

fn coef_sum(p: &Polynomial) -> i64 {
    p.coeffs[..p.size].iter().sum()
}

/// Multiply two polynomials (big-endian coefficient order: index 0 is the
/// highest degree term of the represented value) into `out`, reducing
/// coefficients modulo `q`.
fn poly_mul(a: &Polynomial, b: &Polynomial, out: &mut Polynomial, q: u64) {
    let qi = q as i64;
    let out_len = out.coeffs.len();
    for c in out.coeffs.iter_mut() {
        *c = 0;
    }
    for i in 0..a.size {
        for j in 0..b.size {
            let deg = (a.size - 1 - i) + (b.size - 1 - j);
            if deg < out_len {
                let idx = out_len - 1 - deg;
                out.coeffs[idx] =
                    (out.coeffs[idx] + a.coeffs[i] * b.coeffs[j]).rem_euclid(qi);
            }
        }
    }
    out.size = out_len;
}

/// Add two polynomials (right aligned, i.e. lowest degree term at the last
/// index of the destination buffer) into `out`, modulo `q`.
fn poly_add(a: &Polynomial, b: &Polynomial, out: &mut Polynomial, q: u64) {
    let qi = q as i64;
    let len = out.coeffs.len();
    for c in out.coeffs.iter_mut() {
        *c = 0;
    }
    for i in 0..a.size {
        let idx = len - a.size + i;
        out.coeffs[idx] = (out.coeffs[idx] + a.coeffs[i]).rem_euclid(qi);
    }
    for i in 0..b.size {
        let idx = len - b.size + i;
        out.coeffs[idx] = (out.coeffs[idx] + b.coeffs[i]).rem_euclid(qi);
    }
    out.size = len;
}

/// Reduce `poly` modulo the (monic) ring polynomial `u`, in place.
fn poly_mod(poly: &mut Polynomial, u: &Polynomial, q: u64) {
    let qi = q as i64;
    let dim = u.size - 1;

    if poly.size <= dim {
        return;
    }

    let reducible = poly.size - dim;
    for idx in 0..reducible {
        let coeff = poly.coeffs[idx].rem_euclid(qi);
        if coeff == 0 {
            continue;
        }
        for k in 0..u.size {
            let target = idx + k;
            if target < poly.size {
                poly.coeffs[target] =
                    (poly.coeffs[target] - coeff * u.coeffs[k]).rem_euclid(qi);
            }
        }
    }

    let start = poly.size - dim;
    let reduced: Vec<i64> = poly.coeffs[start..poly.size].to_vec();
    poly.coeffs[..dim].copy_from_slice(&reduced);
    poly.size = dim;
}

// ---------------------------------------------------------------------
// Matrix helpers used by `generate_secret`.
// ---------------------------------------------------------------------

fn mod_inv(a: i64, q: i64) -> Option<i64> {
    let mut old_r = a.rem_euclid(q);
    let mut r = q;
    let mut old_s: i64 = 1;
    let mut s: i64 = 0;

    while r != 0 {
        let quotient = old_r / r;
        let tmp_r = old_r - quotient * r;
        old_r = r;
        r = tmp_r;

        let tmp_s = old_s - quotient * s;
        old_s = s;
        s = tmp_s;
    }

    if old_r != 1 {
        None
    } else {
        Some(old_s.rem_euclid(q))
    }
}

fn matrix_inverse(m: &[Vec<u64>], q: u64) -> Option<Vec<Vec<u64>>> {
    let n = m.len();
    let qi = q as i64;

    let mut a: Vec<Vec<i64>> = m
        .iter()
        .map(|row| row.iter().map(|&v| (v as i64).rem_euclid(qi)).collect())
        .collect();
    let mut inv: Vec<Vec<i64>> = (0..n)
        .map(|i| (0..n).map(|j| if i == j { 1 } else { 0 }).collect())
        .collect();

    for col in 0..n {
        let mut pivot_row = None;
        for r in col..n {
            if a[r][col] != 0 && mod_inv(a[r][col], qi).is_some() {
                pivot_row = Some(r);
                break;
            }
        }
        let pivot_row = pivot_row?;
        a.swap(col, pivot_row);
        inv.swap(col, pivot_row);

        let inv_pivot = mod_inv(a[col][col], qi)?;
        for j in 0..n {
            a[col][j] = (a[col][j] * inv_pivot).rem_euclid(qi);
            inv[col][j] = (inv[col][j] * inv_pivot).rem_euclid(qi);
        }

        for r in 0..n {
            if r != col {
                let factor = a[r][col];
                if factor != 0 {
                    for j in 0..n {
                        a[r][j] = (a[r][j] - factor * a[col][j]).rem_euclid(qi);
                        inv[r][j] = (inv[r][j] - factor * inv[col][j]).rem_euclid(qi);
                    }
                }
            }
        }
    }

    Some(
        inv.iter()
            .map(|row| row.iter().map(|&v| v as u64).collect())
            .collect(),
    )
}

fn matrix_multiply(a: &[Vec<u64>], b: &[Vec<u64>], out: &mut Vec<Vec<u64>>, q: u64) {
    let n = a.len();
    let qi = q as i64;
    for i in 0..n {
        for j in 0..n {
            let mut sum: i64 = 0;
            for k in 0..n {
                sum += a[i][k] as i64 * b[k][j] as i64;
            }
            out[i][j] = sum.rem_euclid(qi) as u64;
        }
    }
}

fn fill_random_invertible_pairs(dim: usize, q: u64, max_tries: usize) -> (Vec<Vec<u64>>, Vec<Vec<u64>>) {
    let mut tries: usize = 0;
    loop {
        let m: Vec<Vec<u64>> = (0..dim)
            .map(|_| {
                (0..dim)
                    .map(|_| randrange(0, q.saturating_sub(1)))
                    .collect()
            })
            .collect();

        if let Some(inv) = matrix_inverse(&m, q) {
            return (m, inv);
        }

        tries += 1;
        if tries >= max_tries {
            // Keep trying: a random matrix over Zq is invertible with
            // overwhelming probability, so this loop terminates quickly in
            // practice even beyond the "hint" try count from the original C
            // implementation.
            continue;
        }
    }
}

// ---------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------

/// Generate an error element `rm` over Zq[X]₍u₎.
pub fn generate_error(q: u64, message: u64, rm: &mut Polynomial) -> Result<()> {
    for i in 0..rm.size {
        rm.coeffs[i] = randrange(0, q) as i64;
    }

    let sum = coef_sum(rm);
    let last = rm.size - 1;
    let qi = q as i64;
    let shift = (rm.coeffs[last] + (message as i64 - sum)) % qi;
    rm.coeffs[last] = if shift > 0 { shift } else { shift + qi };

    Ok(())
}

/// Generate a vanisher vector `e` over Zq[X]₍u₎.
pub fn generate_vanisher(p: u64, q: u64, e: &mut Polynomial) -> Result<()> {
    let k: i64 = if (randrange(0, 1) as f64) < EPROB { 0 } else { 1 };

    for i in 0..e.size {
        e.coeffs[i] = randrange(0, q) as i64;
    }

    let sum = coef_sum(e);
    let last = e.size - 1;
    let qi = q as i64;
    let shift = (e.coeffs[last] + p as i64 * k - sum) % qi;
    e.coeffs[last] = if shift > 0 { shift } else { shift + qi };

    Ok(())
}

/// Generate a linear vector `b` over Zq[X]₍u₎.
pub fn generate_linear(p: u64, q: u64, b: &mut Polynomial) -> Result<()> {
    let k = randrange(0, p) as i64;

    for i in 0..b.size {
        b.coeffs[i] = randrange(0, q) as i64;
    }

    let sum = coef_sum(b);
    let last = b.size - 1;
    let qi = q as i64;
    let shift = (b.coeffs[last] + k - sum) % qi;
    b.coeffs[last] = if shift > 0 { shift } else { shift + qi };

    Ok(())
}

/// Generate the polynomial `u` for the arithmetic channel.
pub fn generate_u(channel: &Channel, param: &Parameters, u: &mut Polynomial) -> Result<()> {
    let dim = param.dim;

    let mut nonzeros = randrange(dim as u64 / 2, dim as u64 - 1) as usize;
    let mut zeroes = dim - nonzeros;

    u.coeffs[0] = 1;

    let mut i: usize = 1;
    while i < dim {
        if nonzeros > 1 {
            u.coeffs[i] = randrange(0, channel.q) as i64;
            i += 1;
            nonzeros -= 1;
        } else {
            break;
        }

        if zeroes > 0 {
            let samp = clamp(0, zeroes as u64, normal_rand(zeroes as u64 / 2, zeroes as u64 / 2)) as usize;
            let zero = randrange(0, samp as u64) as usize;
            for _ in 0..zero {
                if i >= dim {
                    break;
                }
                u.coeffs[i] = 0;
                i += 1;
            }
            zeroes -= zero;
        }
    }

    u.coeffs[dim] = 0;
    u.coeffs[dim] = channel.q as i64 - coef_sum(u);

    Ok(())
}

/// Generate the secret key for the arithmetic channel.
pub fn generate_secret(
    channel: &Channel,
    param: &Parameters,
    u: &Polynomial,
    secret: &mut PolyArray,
    lambda: &mut Matrix3D,
) -> Result<()> {
    let dim = param.dim;
    let q = channel.q;

    let (m, invm) = fill_random_invertible_pairs(dim, q, 600);

    secret.size = dim;
    for i in 0..dim {
        for j in 0..dim {
            secret.polies[i].coeffs[j] = m[j][i] as i64;
        }
    }

    for i in 0..secret.size {
        let mut arr = vec![vec![0u64; dim]; dim];

        for j in 0..secret.size {
            let mut a_ij_poly = new_poly(2 * secret.size);
            poly_mul(&secret.polies[i], &secret.polies[j], &mut a_ij_poly, q);
            poly_mod(&mut a_ij_poly, u, q);

            for row in 0..dim {
                arr[row][j] = a_ij_poly.coeffs[dim - row - 1] as u64;
            }
        }

        let mut result = vec![vec![0u64; dim]; dim];
        matrix_multiply(&invm, &arr, &mut result, q);
        lambda.data[i] = result;
    }

    Ok(())
}

/// Generate the polynomial array `f0` for the public key.
pub fn generate_f0(channel: &Channel, _param: &Parameters, f0: &mut PolyArray) -> Result<()> {
    for i in 0..f0.size {
        for j in 0..f0.polies[i].size {
            f0.polies[i].coeffs[j] = randrange(0, channel.q - 1) as i64;
        }
    }

    Ok(())
}

/// Generate the polynomial `f1` for the public key.
pub fn generate_f1(
    channel: &Channel,
    param: &Parameters,
    f0: &PolyArray,
    x: &PolyArray,
    u: &Polynomial,
    f1: &mut Polynomial,
) -> Result<()> {
    let dim = param.dim;
    let mut f_pre = new_poly(dim * 2);
    set_zero(&mut f_pre);

    for i in 0..dim {
        let mut tmp = new_poly(dim * 2);
        poly_mul(&f0.polies[i], &x.polies[i], &mut tmp, channel.q);

        let mut new_f_pre = new_poly(dim * 2);
        poly_add(&f_pre, &tmp, &mut new_f_pre, channel.q);
        f_pre = new_f_pre;
    }

    poly_mod(&mut f_pre, u, channel.q);

    if f1.size < f_pre.size {
        return Err(AcesError::InvalidLength);
    }

    let diff = f1.size - f_pre.size;
    let start = diff;
    f1.coeffs[start..start + f_pre.size].copy_from_slice(&f_pre.coeffs[..f_pre.size]);

    let shifted: Vec<i64> = f1.coeffs[start..].to_vec();
    f1.coeffs = shifted;
    f1.size = f_pre.size;

    Ok(())
}
