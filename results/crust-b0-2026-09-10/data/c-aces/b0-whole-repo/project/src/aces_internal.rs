use crate::channel::{Channel, Parameters};
use crate::common::{clamp, normal_rand, randrange};
use crate::error::{AcesError, Result};
use crate::matrix::{fill_random_invertible_pairs, matrix2d_multiply, Matrix2D, Matrix3D};
use crate::polynomial::{PolyArray, Polynomial};

const EPROB: f64 = 0.5;

/// Generate an error element `rm` over Zq[X]₍u₎.
pub fn generate_error(q: u64, message: u64, rm: &mut Polynomial) -> Result<()> {
    let size = rm.coeffs.len();
    if size == 0 {
        return Err(AcesError::GenericError("empty polynomial".into()));
    }
    for i in 0..size {
        rm.coeffs[i] = randrange(0, q) as i64;
    }
    let last = size - 1;
    let shift =
        (rm.coeffs[last].wrapping_add(message as i64).wrapping_sub(rm.coef_sum())) % (q as i64);
    rm.coeffs[last] = if shift > 0 { shift } else { shift + q as i64 };
    Ok(())
}
/// Generate a vanisher vector `e` over Zq[X]₍u₎.
pub fn generate_vanisher(p: u64, q: u64, e: &mut Polynomial) -> Result<()> {
    let r = randrange(0, 1);
    let k: i64 = if (r as f64) < EPROB { 0 } else { 1 };
    let size = e.coeffs.len();
    if size == 0 {
        return Err(AcesError::GenericError("empty polynomial".into()));
    }
    for i in 0..size {
        e.coeffs[i] = randrange(0, q) as i64;
    }
    let last = size - 1;
    let shift = (e.coeffs[last]
        .wrapping_add((p as i64).wrapping_mul(k))
        .wrapping_sub(e.coef_sum()))
        % (q as i64);
    e.coeffs[last] = if shift > 0 { shift } else { shift + q as i64 };
    Ok(())
}
/// Generate a linear vector `b` over Zq[X]₍u₎.
pub fn generate_linear(p: u64, q: u64, b: &mut Polynomial) -> Result<()> {
    let k = randrange(0, p) as i64;
    let size = b.coeffs.len();
    if size == 0 {
        return Err(AcesError::GenericError("empty polynomial".into()));
    }
    for i in 0..size {
        b.coeffs[i] = randrange(0, q) as i64;
    }
    let last = size - 1;
    let shift = (b.coeffs[last].wrapping_add(k).wrapping_sub(b.coef_sum())) % (q as i64);
    b.coeffs[last] = if shift > 0 { shift } else { shift + q as i64 };
    Ok(())
}
/// Generate the polynomial `u` for the arithmetic channel.
pub fn generate_u(channel: &Channel, param: &Parameters, u: &mut Polynomial) -> Result<()> {
    let dim = param.dim as usize;
    if u.coeffs.len() < dim + 1 {
        return Err(AcesError::GenericError("u polynomial too small".into()));
    }
    let mut nonzeros = randrange(param.dim / 2, param.dim - 1);
    let mut zeroes = param.dim - nonzeros;
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
            let samp = clamp(
                0,
                zeroes,
                normal_rand((zeroes / 2) as f64, (zeroes / 2) as f64) as u64,
            );
            let zero = randrange(0, samp);
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
    u.coeffs[dim] = channel.q as i64 - u.coef_sum();
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
    let dim = param.dim as usize;
    let mut m = Matrix2D::new(dim);
    let mut invm = Matrix2D::new(dim);
    fill_random_invertible_pairs(&mut m, &mut invm, channel.q, 600)?;

    if secret.polies.len() != dim {
        return Err(AcesError::GenericError("secret size mismatch".into()));
    }

    for i in 0..dim {
        for j in 0..dim {
            secret.polies[i].coeffs[j] = m
                .get(j, i)
                .ok_or_else(|| AcesError::GenericError("idx".into()))? as i64;
        }
    }

    let mut arr = m;
    for i in 0..dim {
        for j in 0..dim {
            let mut prod = secret.polies[i].mul(&secret.polies[j], channel.q)?;
            prod.poly_mod(u, channel.q)?;

            let plen = prod.coeffs.len();
            let mut padded = vec![0i64; dim];
            if plen <= dim {
                padded[dim - plen..dim].copy_from_slice(&prod.coeffs);
            } else {
                padded.copy_from_slice(&prod.coeffs[plen - dim..plen]);
            }

            for row in 0..dim {
                arr.set(row, j, padded[dim - row - 1] as u64)?;
            }
        }
        let result = matrix2d_multiply(&invm, &arr, channel.q)?;
        let slot = lambda
            .get_mut(i)
            .ok_or_else(|| AcesError::GenericError("lambda index".into()))?;
        *slot = result;
    }

    Ok(())
}
/// Generate the polynomial array `f0` for the public key.
pub fn generate_f0(channel: &Channel, param: &Parameters, f0: &mut PolyArray) -> Result<()> {
    let _ = param;
    for poly in f0.polies.iter_mut() {
        let len = poly.coeffs.len();
        for j in 0..len {
            poly.coeffs[j] = randrange(0, channel.q - 1) as i64;
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
    let dim = param.dim as usize;
    let mut f_pre = Polynomial::new(vec![0i64; dim * 2]);
    for i in 0..dim {
        let tmp = f0.polies[i].mul(&x.polies[i], channel.q)?;
        f_pre = f_pre.add(&tmp, channel.q)?;
    }
    f_pre.poly_mod(u, channel.q)?;
    *f1 = f_pre;
    Ok(())
}
