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
        return Err(AcesError::GenericError("empty polynomial".to_string()));
    }

    for i in 0..size {
        rm.coeffs[i] = randrange(0, q) as i64;
    }

    let sum = rm.coef_sum();
    let shift = (rm.coeffs[size - 1]
        .wrapping_add(message as i64)
        .wrapping_sub(sum))
        % (q as i64);
    rm.coeffs[size - 1] = if shift > 0 { shift } else { shift + q as i64 };

    Ok(())
}

/// Generate a vanisher vector `e` over Zq[X]₍u₎.
pub fn generate_vanisher(p: u64, q: u64, e: &mut Polynomial) -> Result<()> {
    let size = e.coeffs.len();
    if size == 0 {
        return Err(AcesError::GenericError("empty polynomial".to_string()));
    }

    let k: i64 = if (randrange(0, 1) as f64) < EPROB { 0 } else { 1 };

    for i in 0..size {
        e.coeffs[i] = randrange(0, q) as i64;
    }

    let sum = e.coef_sum();
    let shift = (e.coeffs[size - 1]
        .wrapping_add((p as i64).wrapping_mul(k))
        .wrapping_sub(sum))
        % (q as i64);
    e.coeffs[size - 1] = if shift > 0 { shift } else { shift + q as i64 };

    Ok(())
}

/// Generate a linear vector `b` over Zq[X]₍u₎.
pub fn generate_linear(p: u64, q: u64, b: &mut Polynomial) -> Result<()> {
    let size = b.coeffs.len();
    if size == 0 {
        return Err(AcesError::GenericError("empty polynomial".to_string()));
    }

    let k = randrange(0, p) as i64;

    for i in 0..size {
        b.coeffs[i] = randrange(0, q) as i64;
    }

    let sum = b.coef_sum();
    let shift = (b.coeffs[size - 1].wrapping_add(k).wrapping_sub(sum)) % (q as i64);
    b.coeffs[size - 1] = if shift > 0 { shift } else { shift + q as i64 };

    Ok(())
}

/// Generate the polynomial `u` for the arithmetic channel.
pub fn generate_u(channel: &Channel, param: &Parameters, u: &mut Polynomial) -> Result<()> {
    let dim = param.dim;
    if (u.coeffs.len() as u64) < dim + 1 {
        return Err(AcesError::GenericError(
            "u polynomial too small".to_string(),
        ));
    }

    let mut nonzeros = randrange(dim / 2, dim - 1);
    let mut zeroes = dim - nonzeros;
    u.coeffs[0] = 1;

    let mut i: u64 = 1;
    while i < dim {
        if nonzeros > 1 {
            u.coeffs[i as usize] = randrange(0, channel.q) as i64;
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
                u.coeffs[i as usize] = 0;
                i += 1;
            }
            zeroes -= zero;
        }
    }

    u.coeffs[dim as usize] = 0;
    let sum = u.coef_sum();
    u.coeffs[dim as usize] = (channel.q as i64).wrapping_sub(sum);

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

    let mut new_polies = Vec::with_capacity(dim);
    for i in 0..dim {
        let coeffs: Vec<i64> = (0..dim).map(|j| m.get(j, i).unwrap() as i64).collect();
        new_polies.push(Polynomial::new(coeffs));
    }
    secret.polies = new_polies;

    for i in 0..dim {
        for j in 0..dim {
            let mut a_ij_poly = secret.polies[i].mul(&secret.polies[j], channel.q)?;
            a_ij_poly.poly_mod(u, channel.q)?;

            for row in 0..dim {
                let val = a_ij_poly.coeffs[dim - row - 1];
                m.set(row, j, val as u64)?;
            }
        }

        let lam = matrix2d_multiply(&invm, &m, channel.q)?;
        if let Some(target) = lambda.get_mut(i) {
            *target = lam;
        } else {
            return Err(AcesError::GenericError(
                "lambda index out of bounds".to_string(),
            ));
        }
    }

    Ok(())
}

/// Generate the polynomial array `f0` for the public key.
pub fn generate_f0(channel: &Channel, _param: &Parameters, f0: &mut PolyArray) -> Result<()> {
    for poly in f0.polies.iter_mut() {
        for c in poly.coeffs.iter_mut() {
            *c = randrange(0, channel.q - 1) as i64;
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
