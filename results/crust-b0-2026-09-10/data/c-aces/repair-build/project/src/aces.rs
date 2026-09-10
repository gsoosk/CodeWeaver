use crate::channel::{Channel, Parameters};
use crate::error::{AcesError, Result};
use crate::matrix::Matrix3D;
use crate::polynomial::{PolyArray, Polynomial};

use std::time::{SystemTime, UNIX_EPOCH};

/// Represents the public key for the arithmetic channel.
#[derive(Debug, Clone)]
pub struct PublicKey {
    pub u: Polynomial,
    pub lambda: Matrix3D,
}
/// Represents the private key for the arithmetic channel.
#[derive(Debug, Clone)]
pub struct PrivateKey {
    pub x: PolyArray,
    pub f0: PolyArray,
    pub f1: Polynomial,
}
/// Shared information for the arithmetic channel.
#[derive(Debug, Clone)]
pub struct SharedInfo {
    pub channel: Channel,
    pub param: Parameters,
    pub pk: PublicKey,
}
/// An instance of the ACES encryption scheme.
#[derive(Debug, Clone)]
pub struct Aces {
    pub shared_info: SharedInfo,
    pub private_key: PrivateKey,
}
/// A ciphertext in the ACES framework.
#[derive(Debug, Clone)]
pub struct CipherMessage {
    pub c1: PolyArray,
    pub c2: Polynomial,
    pub level: u64,
}

// ---------------------------------------------------------------------
// Internal helpers.
//
// These mirror the routines that in the original C implementation lived
// in the private "Aces-internal.h"/"Aces-internal.c" files. Since those
// were not part of the translation unit handed to us, the necessary
// polynomial arithmetic and key-material generation routines are
// re-implemented here, faithfully following the algebraic structure
// described by the public `Aces.h` documentation (evaluation at the
// integer point ω = 1, i.e. the sum of a polynomial's coefficients).
// ---------------------------------------------------------------------

struct Rng(u64);

impl Rng {
    fn new() -> Self {
        let seed = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64
            | 1;
        Rng(seed)
    }

    fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x
    }

    fn next_mod(&mut self, m: u64) -> u64 {
        if m == 0 {
            0
        } else {
            self.next_u64() % m
        }
    }
}

fn poly_zero(size: usize) -> Polynomial {
    Polynomial {
        coeffs: vec![0u64; size],
    }
}

fn poly_add(a: &Polynomial, b: &Polynomial, q: u64) -> Polynomial {
    let n = a.coeffs.len().max(b.coeffs.len());
    let mut out = vec![0u64; n];
    for i in 0..n {
        let av = *a.coeffs.get(i).unwrap_or(&0) % q;
        let bv = *b.coeffs.get(i).unwrap_or(&0) % q;
        out[i] = (av + bv) % q;
    }
    Polynomial { coeffs: out }
}

fn poly_sub(a: &Polynomial, b: &Polynomial, q: u64) -> Polynomial {
    let n = a.coeffs.len().max(b.coeffs.len());
    let mut out = vec![0u64; n];
    for i in 0..n {
        let av = (*a.coeffs.get(i).unwrap_or(&0) % q) as i128;
        let bv = (*b.coeffs.get(i).unwrap_or(&0) % q) as i128;
        let v = (av - bv).rem_euclid(q as i128);
        out[i] = v as u64;
    }
    Polynomial { coeffs: out }
}

fn poly_mul(a: &Polynomial, b: &Polynomial, q: u64) -> Polynomial {
    if a.coeffs.is_empty() || b.coeffs.is_empty() {
        return Polynomial { coeffs: vec![] };
    }
    let n = a.coeffs.len() + b.coeffs.len() - 1;
    let mut out = vec![0u128; n];
    for (i, &av) in a.coeffs.iter().enumerate() {
        if av == 0 {
            continue;
        }
        for (j, &bv) in b.coeffs.iter().enumerate() {
            out[i + j] += (av as u128) * (bv as u128);
        }
    }
    Polynomial {
        coeffs: out
            .into_iter()
            .map(|v| (v % q as u128) as u64)
            .collect(),
    }
}

fn mod_inverse(a: u64, m: u64) -> u64 {
    let (mut old_r, mut r) = (a as i128, m as i128);
    let (mut old_s, mut s) = (1i128, 0i128);
    while r != 0 {
        let quotient = old_r / r;
        let tmp_r = old_r - quotient * r;
        old_r = r;
        r = tmp_r;
        let tmp_s = old_s - quotient * s;
        old_s = s;
        s = tmp_s;
    }
    ((old_s % m as i128 + m as i128) % m as i128) as u64
}

fn poly_mod(a: &Polynomial, u: &Polynomial, q: u64) -> Polynomial {
    let u_deg = u.coeffs.len().saturating_sub(1);
    if u_deg == 0 {
        return Polynomial { coeffs: vec![] };
    }
    let mut rem = a.coeffs.clone();
    let u_lead = u.coeffs[u_deg] % q;
    let inv_lead = mod_inverse(if u_lead == 0 { 1 } else { u_lead }, q);

    while rem.len() > u_deg {
        let cur_deg = rem.len() - 1;
        let lead = rem[cur_deg] % q;
        if lead != 0 {
            let factor = ((lead as u128) * (inv_lead as u128) % q as u128) as u64;
            let shift = cur_deg - u_deg;
            for (i, &uc) in u.coeffs.iter().enumerate() {
                let idx = i + shift;
                if idx >= rem.len() {
                    break;
                }
                let sub = ((factor as u128) * ((uc % q) as u128) % q as u128) as u64;
                let v = (rem[idx] as i128 - sub as i128).rem_euclid(q as i128);
                rem[idx] = v as u64;
            }
        }
        rem.pop();
    }
    if rem.len() < u_deg {
        rem.resize(u_deg, 0);
    }
    Polynomial { coeffs: rem }
}

fn poly_fit(a: &Polynomial, q: u64) -> Polynomial {
    Polynomial {
        coeffs: a.coeffs.iter().map(|&c| c % q).collect(),
    }
}

fn coef_sum(a: &Polynomial) -> u64 {
    a.coeffs.iter().fold(0u64, |acc, &c| acc.wrapping_add(c))
}

fn poly_sub_scaler(a: &Polynomial, scalar: u64, q: u64) -> Polynomial {
    let mut out = a.coeffs.clone();
    if !out.is_empty() {
        let v = (out[0] as i128 - (scalar % q) as i128).rem_euclid(q as i128);
        out[0] = v as u64;
    }
    Polynomial { coeffs: out }
}

fn eval1(a: &Polynomial, q: u64) -> u64 {
    let mut s: u128 = 0;
    for &c in &a.coeffs {
        s += (c % q) as u128;
    }
    (s % q as u128) as u64
}

/// Creates a random polynomial of the given size whose coefficient sum
/// equals `target` modulo `q` (this corresponds to the polynomial's
/// evaluation at X = 1, the integer point ω referred to in the
/// documentation).
fn random_poly_with_sum(size: usize, target: u64, q: u64, rng: &mut Rng) -> Polynomial {
    let mut coeffs = vec![0u64; size];
    if size == 0 {
        return Polynomial { coeffs };
    }
    let mut sum: u128 = 0;
    for c in coeffs.iter_mut().skip(1) {
        let v = rng.next_mod(q.max(1));
        *c = v;
        sum += v as u128;
    }
    let target = target % q.max(1);
    let rest = (sum % q.max(1) as u128) as u64;
    let c0 = (target as i128 - rest as i128).rem_euclid(q.max(1) as i128) as u64;
    coeffs[0] = c0;
    Polynomial { coeffs }
}

fn generate_u(channel: &Channel, param: &Parameters, rng: &mut Rng) -> Polynomial {
    let dim = param.dim as usize;
    let q = channel.q;
    let mut poly = random_poly_with_sum(dim, (q + q - 1) % q, q, rng);
    poly.coeffs.push(1 % q);
    poly
}

fn generate_secret(
    channel: &Channel,
    param: &Parameters,
    _u: &Polynomial,
    rng: &mut Rng,
) -> (PolyArray, Matrix3D) {
    let dim = param.dim as usize;
    let q = channel.q;
    let mut polies = Vec::with_capacity(dim);
    for _ in 0..dim {
        let mut coeffs = vec![0u64; dim];
        for c in coeffs.iter_mut() {
            *c = rng.next_mod(q);
        }
        polies.push(Polynomial { coeffs });
    }
    let x = PolyArray { polies };
    let data = vec![vec![vec![0u64; dim]; dim]; dim];
    let lambda = Matrix3D { data };
    (x, lambda)
}

fn generate_f0(channel: &Channel, param: &Parameters, rng: &mut Rng) -> PolyArray {
    let dim = param.dim as usize;
    let q = channel.q;
    let mut polies = Vec::with_capacity(dim);
    for _ in 0..dim {
        let mut coeffs = vec![0u64; dim];
        for c in coeffs.iter_mut() {
            *c = rng.next_mod(q);
        }
        polies.push(Polynomial { coeffs });
    }
    PolyArray { polies }
}

fn generate_f1(
    channel: &Channel,
    param: &Parameters,
    f0: &PolyArray,
    x: &PolyArray,
    rng: &mut Rng,
) -> Polynomial {
    let dim = param.dim as usize;
    let q = channel.q;
    let mut target: u128 = 0;
    for i in 0..dim {
        let a = eval1(&f0.polies[i], q) as u128;
        let b = eval1(&x.polies[i], q) as u128;
        target += a * b;
    }
    let target = (target % q.max(1) as u128) as u64;
    random_poly_with_sum(dim, target, q, rng)
}

fn generate_error(q: u64, message: u64, dim: usize, rng: &mut Rng) -> Polynomial {
    random_poly_with_sum(dim, message % q.max(1), q, rng)
}

fn generate_vanisher(p: u64, q: u64, dim: usize, rng: &mut Rng) -> Polynomial {
    let l = rng.next_mod(2);
    let target = (p.wrapping_mul(l)) % q.max(1);
    random_poly_with_sum(dim, target, q, rng)
}

fn generate_linear(p: u64, q: u64, dim: usize, rng: &mut Rng) -> Polynomial {
    let target = rng.next_mod(p + 1);
    random_poly_with_sum(dim, target % q.max(1), q, rng)
}

// ---------------------------------------------------------------------
// Public API.
// ---------------------------------------------------------------------

/// Set up the ACES instance (using external memory, for example).
pub fn set_aces(aces: &mut Aces, dim: usize, mem: &mut [u8]) -> Result<()> {
    let coeff_size = std::mem::size_of::<u64>();
    let required = coeff_size * (2 * dim + 1 + 2 * dim * dim) + coeff_size * dim * dim * dim;

    if mem.len() < required {
        return Err(AcesError::InsufficientMemory);
    }

    aces.shared_info.pk.u = poly_zero(dim + 1);
    aces.shared_info.pk.lambda = Matrix3D {
        data: vec![vec![vec![0u64; dim]; dim]; dim],
    };
    aces.private_key.x = PolyArray {
        polies: (0..dim).map(|_| poly_zero(dim)).collect(),
    };
    aces.private_key.f0 = PolyArray {
        polies: (0..dim).map(|_| poly_zero(dim)).collect(),
    };
    aces.private_key.f1 = poly_zero(dim);

    Ok(())
}

/// Initialize an instance of ACES.
pub fn init_aces(p: u64, q: u64, dim: u64, aces: &mut Aces) -> Result<()> {
    aces.shared_info.param.dim = dim;
    aces.shared_info.param.n = 1;
    aces.shared_info.channel = Channel { p, q, n: 1 };

    let mut rng = Rng::new();

    aces.shared_info.pk.u =
        generate_u(&aces.shared_info.channel, &aces.shared_info.param, &mut rng);

    let (x, lambda) = generate_secret(
        &aces.shared_info.channel,
        &aces.shared_info.param,
        &aces.shared_info.pk.u,
        &mut rng,
    );
    aces.private_key.x = x;
    aces.shared_info.pk.lambda = lambda;

    aces.private_key.f0 = generate_f0(&aces.shared_info.channel, &aces.shared_info.param, &mut rng);

    aces.private_key.f1 = generate_f1(
        &aces.shared_info.channel,
        &aces.shared_info.param,
        &aces.private_key.f0,
        &aces.private_key.x,
        &mut rng,
    );

    Ok(())
}

/// Encrypt a message.
pub fn aces_encrypt(aces: &Aces, message: &[u64], result: &mut CipherMessage) -> Result<()> {
    if message.len() > 1 {
        return Err(AcesError::InvalidLength);
    }
    let dim = aces.shared_info.param.dim as usize;
    let q = aces.shared_info.channel.q;
    let p = aces.shared_info.channel.p;
    let mut rng = Rng::new();

    let r_m = generate_error(q, message[0], dim, &mut rng);
    let e = generate_vanisher(p, q, dim, &mut rng);
    let b = generate_linear(p, q, dim, &mut rng);

    // C1
    let polies: Vec<Polynomial> = (0..dim)
        .map(|i| {
            let tmp = poly_mul(&b, &aces.private_key.f0.polies[i], q);
            poly_mod(&tmp, &aces.shared_info.pk.u, q)
        })
        .collect();
    result.c1 = PolyArray { polies };

    // C2
    let f1_plus_e = poly_add(&aces.private_key.f1, &e, q);
    let tmp = poly_mul(&f1_plus_e, &b, q);
    let tmp = poly_add(&tmp, &r_m, q);
    let tmp = poly_mod(&tmp, &aces.shared_info.pk.u, q);
    result.c2 = tmp;

    // Level
    result.level = p;

    Ok(())
}

/// Decrypt a ciphertext.
pub fn aces_decrypt(aces: &Aces, message: &CipherMessage, result: &mut [u64]) -> Result<()> {
    if result.len() > 1 {
        return Err(AcesError::InvalidLength);
    }
    let dim = aces.shared_info.param.dim as usize;
    let q = aces.shared_info.channel.q;
    let p = aces.shared_info.channel.p;

    let mut c0tx = poly_zero(1);
    for i in 0..dim {
        let tmp = poly_mul(&message.c1.polies[i], &aces.private_key.x.polies[i], q);
        c0tx = poly_add(&tmp, &c0tx, q);
    }

    let c0tx = poly_fit(&c0tx, q);
    let c0tx = poly_sub(&message.c2, &c0tx, q);

    result[0] = (coef_sum(&c0tx) % q) % p;
    Ok(())
}

/// Perform homomorphic addition on two ciphertexts.
pub fn aces_add(
    a: &CipherMessage,
    b: &CipherMessage,
    info: &SharedInfo,
    result: &mut CipherMessage,
) -> Result<()> {
    let dim = info.param.dim as usize;
    let q = info.channel.q;

    let polies: Vec<Polynomial> = (0..dim)
        .map(|i| {
            let tmp = poly_add(&a.c1.polies[i], &b.c1.polies[i], q);
            poly_mod(&tmp, &info.pk.u, q)
        })
        .collect();
    result.c1 = PolyArray { polies };

    let tmp = poly_add(&a.c2, &b.c2, q);
    result.c2 = poly_mod(&tmp, &info.pk.u, q);

    result.level = a.level + b.level;
    Ok(())
}

/// Perform homomorphic multiplication on two ciphertexts.
pub fn aces_mul(
    a: &CipherMessage,
    b: &CipherMessage,
    info: &SharedInfo,
    result: &mut CipherMessage,
) -> Result<()> {
    // Mirrors the original C implementation, which is a stub (TODO) that
    // performs no actual computation.
    let _ = (a, b, info, result);
    Ok(())
}

/// Refresh a ciphertext to mitigate level increase.
pub fn aces_refresh(info: &SharedInfo, message: &mut CipherMessage, level: u64) -> Result<()> {
    let q = info.channel.q;
    let p = info.channel.p;
    message.c2 = poly_sub_scaler(&message.c2, level.wrapping_mul(p), q);
    message.level = message.level.wrapping_sub(level);
    Ok(())
}
