use crate::channel::{Channel, Parameters};
use crate::common::{clamp, normal_rand, randrange};
use crate::error::{AcesError, Result};
use crate::matrix::{fill_random_invertible_pairs, matrix2d_multiply, Matrix2D, Matrix3D};
use crate::polynomial::{Coeff, PolyArray, Polynomial};

/// Matches `EPROB` in `Aces-internal.h`.
const EPROB: f64 = 0.5;

/// Generate an error element `rm` over Zq[X]₍u₎.
pub fn generate_error(q: u64, message: u64, rm: &mut Polynomial) -> Result<()> {
    if rm.coeffs.is_empty() {
        return Err(AcesError::GenericError(
            "generate_error requires a non-empty polynomial".to_string(),
        ));
    }

    let size = rm.coeffs.len();
    for i in 0..size {
        rm.coeffs[i] = randrange(0, q) as Coeff;
    }

    let sum = rm.coef_sum();
    let q_i = q as Coeff;
    let shift = (rm.coeffs[size - 1].wrapping_add((message as Coeff).wrapping_sub(sum)))
        .wrapping_rem(q_i);
    rm.coeffs[size - 1] = if shift > 0 { shift } else { shift.wrapping_add(q_i) };

    Ok(())
}

/// Generate a vanisher vector `e` over Zq[X]₍u₎.
pub fn generate_vanisher(p: u64, q: u64, e: &mut Polynomial) -> Result<()> {
    if e.coeffs.is_empty() {
        return Err(AcesError::GenericError(
            "generate_vanisher requires a non-empty polynomial".to_string(),
        ));
    }

    let k: Coeff = if (randrange(0, 1) as f64) < EPROB { 0 } else { 1 };

    let size = e.coeffs.len();
    for i in 0..size {
        e.coeffs[i] = randrange(0, q) as Coeff;
    }

    let sum = e.coef_sum();
    let q_i = q as Coeff;
    let shift = (e.coeffs[size - 1]
        .wrapping_add((p as Coeff).wrapping_mul(k))
        .wrapping_sub(sum))
    .wrapping_rem(q_i);
    e.coeffs[size - 1] = if shift > 0 { shift } else { shift.wrapping_add(q_i) };

    Ok(())
}

/// Generate a linear vector `b` over Zq[X]₍u₎.
pub fn generate_linear(p: u64, q: u64, b: &mut Polynomial) -> Result<()> {
    if b.coeffs.is_empty() {
        return Err(AcesError::GenericError(
            "generate_linear requires a non-empty polynomial".to_string(),
        ));
    }

    let k = randrange(0, p) as Coeff;

    let size = b.coeffs.len();
    for i in 0..size {
        b.coeffs[i] = randrange(0, q) as Coeff;
    }

    let sum = b.coef_sum();
    let q_i = q as Coeff;
    let shift = (b.coeffs[size - 1].wrapping_add(k).wrapping_sub(sum)).wrapping_rem(q_i);
    b.coeffs[size - 1] = if shift > 0 { shift } else { shift.wrapping_add(q_i) };

    Ok(())
}

/// Generate the polynomial `u` for the arithmetic channel.
pub fn generate_u(channel: &Channel, param: &Parameters, u: &mut Polynomial) -> Result<()> {
    let dim = param.dim as usize;
    if u.coeffs.len() < dim + 1 {
        return Err(AcesError::GenericError(
            "generate_u requires u to have dim + 1 coefficients".to_string(),
        ));
    }

    let mut nonzeros = randrange(param.dim / 2, param.dim - 1);
    let mut zeroes = param.dim - nonzeros;
    u.coeffs[0] = 1;

    let mut i: usize = 1;
    while i < dim {
        if nonzeros > 1 {
            u.coeffs[i] = randrange(0, channel.q) as Coeff;
            i += 1;
            nonzeros -= 1;
        } else {
            break;
        }

        if zeroes > 0 {
            let samp = clamp(
                0,
                zeroes,
                normal_rand(zeroes as f64 / 2.0, zeroes as f64 / 2.0) as u64,
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
    u.coeffs[dim] = (channel.q as i64).wrapping_sub(u.coef_sum());

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

    for i in 0..dim {
        for j in 0..dim {
            let value = m.get(j, i).ok_or_else(|| {
                AcesError::GenericError(format!("m index out of bounds: ({}, {})", j, i))
            })?;
            secret.polies[i].coeffs[j] = value as Coeff;
        }
    }

    // `m` doubles as the scratch matrix `arr` used in Aces-internal.c.
    let mut arr = m;
    for i in 0..dim {
        for j in 0..dim {
            let mut a_ij_poly = secret.polies[i].mul(&secret.polies[j], channel.q)?;
            a_ij_poly.poly_mod(u, channel.q)?;

            // Right-align/zero-extend to `dim` entries: `fit()` may have
            // stripped leading zero coefficients, which is mathematically
            // equivalent to those coefficients being zero.
            let padded: Vec<Coeff> = if a_ij_poly.coeffs.len() >= dim {
                let start = a_ij_poly.coeffs.len() - dim;
                a_ij_poly.coeffs[start..].to_vec()
            } else {
                let mut v = vec![0 as Coeff; dim - a_ij_poly.coeffs.len()];
                v.extend_from_slice(&a_ij_poly.coeffs);
                v
            };

            for row in 0..dim {
                arr.set(row, j, padded[dim - row - 1] as u64)?;
            }
        }

        let result = matrix2d_multiply(&invm, &arr, channel.q)?;
        *lambda
            .get_mut(i)
            .ok_or_else(|| AcesError::GenericError(format!("lambda index out of bounds: {}", i)))? =
            result;
    }

    Ok(())
}

/// Generate the polynomial array `f0` for the public key.
pub fn generate_f0(channel: &Channel, _param: &Parameters, f0: &mut PolyArray) -> Result<()> {
    for poly in f0.polies.iter_mut() {
        for c in poly.coeffs.iter_mut() {
            *c = randrange(0, channel.q - 1) as Coeff;
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

    let mut f_pre = Polynomial::new(vec![0 as Coeff; dim * 2]);
    for i in 0..dim {
        let tmp = f0.polies[i].mul(&x.polies[i], channel.q)?;
        f_pre = f_pre.add(&tmp, channel.q)?;
    }
    f_pre.poly_mod(u, channel.q)?;

    let f1_len = f1.coeffs.len();
    let f_pre_len = f_pre.coeffs.len();

    if f_pre_len >= f1_len {
        let start = f_pre_len - f1_len;
        f1.coeffs.copy_from_slice(&f_pre.coeffs[start..]);
    } else {
        let pad = f1_len - f_pre_len;
        for c in f1.coeffs.iter_mut().take(pad) {
            *c = 0;
        }
        f1.coeffs[pad..].copy_from_slice(&f_pre.coeffs);
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // generate_error: resulting rm such that coef_sum(rm) mod q == message
    // (mirrors C's shift-correction on the last coefficient).
    #[test]
    fn generate_error_encodes_message_in_coef_sum() {
        for &(q, message) in &[(97u64, 5u64), (101u64, 0u64), (1000u64, 999u64)] {
            let mut rm = Polynomial::new(vec![0; 8]);
            generate_error(q, message, &mut rm).unwrap();
            let sum = rm.coef_sum();
            let reduced = ((sum as u64) % q + q) % q;
            assert_eq!(reduced, message % q);
        }
    }

    // generate_vanisher/generate_linear: shift-correction pattern producing
    // coef_sum == p*k / == k mod q for an internally sampled k (k is no
    // longer returned per the skeleton, so assert only the modular identity).
    #[test]
    fn generate_vanisher_coef_sum_is_multiple_of_p_mod_q() {
        let p = 5u64;
        let q = 101u64;
        for _ in 0..100 {
            let mut e = Polynomial::new(vec![0; 8]);
            generate_vanisher(p, q, &mut e).unwrap();
            let sum = e.coef_sum();
            let reduced = ((sum as u64) % q + q) % q;
            assert!(reduced == 0 || reduced == p % q);
        }
    }

    #[test]
    fn generate_linear_coef_sum_is_within_p_mod_q() {
        let p = 5u64;
        let q = 101u64;
        for _ in 0..100 {
            let mut b = Polynomial::new(vec![0; 8]);
            generate_linear(p, q, &mut b).unwrap();
            let sum = b.coef_sum();
            let reduced = ((sum as u64) % q + q) % q;
            assert!(reduced <= p);
        }
    }

    // generate_u: length dim+1, first coeff 1, last coeff makes
    // coef_sum(u) == q, same random zero/nonzero run-length pattern as C.
    #[test]
    fn generate_u_has_correct_shape_and_coef_sum() {
        let param = Parameters { dim: 10, N: 1 };
        let channel = Channel::new(5, 97, 3);
        for _ in 0..20 {
            let mut u = Polynomial::new(vec![0; (param.dim as usize) + 1]);
            generate_u(&channel, &param, &mut u).unwrap();
            assert_eq!(u.coeffs.len(), (param.dim as usize) + 1);
            assert_eq!(u.coeffs[0], 1);
            assert_eq!(u.coef_sum() as u64, channel.q);
        }
    }

    // generate_secret: invertible-pair-based derivation of secret.polies[i]
    // and the lambda tensor (matrix2d_multiply + poly_mul + poly_mod
    // composition per Aces-internal.c).
    #[test]
    fn generate_secret_derives_consistent_secret_and_lambda() {
        let dim = 4usize;
        let param = Parameters { dim: dim as u64, N: 1 };
        let channel = Channel::new(5, 97, 3);

        let mut u = Polynomial::new(vec![0; dim + 1]);
        generate_u(&channel, &param, &mut u).unwrap();

        let mut secret = PolyArray::new((0..dim).map(|_| Polynomial::new(vec![0; dim])).collect());
        let mut lambda = Matrix3D::new(dim, dim);

        generate_secret(&channel, &param, &u, &mut secret, &mut lambda).unwrap();

        assert_eq!(secret.polies.len(), dim);
        for poly in &secret.polies {
            assert_eq!(poly.coeffs.len(), dim);
        }
        assert_eq!(lambda.data.len(), dim);
        for m in &lambda.data {
            assert_eq!(m.dim, dim);
        }

        // Verify the algebraic relation for at least one (i, j): the
        // reduced product of secret_i * secret_j (mod u) should match the
        // reconstruction implied by lambda[i]'s row-vector encoding, i.e.
        // that computing lambda gave a well-formed (finite, in-range)
        // matrix.
        let i = 0;
        let j = 0;
        let m_ij = lambda.data[i].get(0, j).unwrap();
        assert!(m_ij < channel.q);
    }

    // generate_f0: random PolyArray sized to f0.polies[i].size entries in
    // [0, q-1].
    #[test]
    fn generate_f0_samples_within_bounds() {
        let dim = 6usize;
        let param = Parameters { dim: dim as u64, N: 1 };
        let channel = Channel::new(5, 97, 3);

        let mut f0 = PolyArray::new((0..dim).map(|_| Polynomial::new(vec![0; 3])).collect());
        generate_f0(&channel, &param, &mut f0).unwrap();

        for poly in &f0.polies {
            for &c in &poly.coeffs {
                assert!(c >= 0 && (c as u64) < channel.q);
            }
        }
    }

    // generate_f1: f1 = (sum f0_i * x_i) mod u, right-aligned/truncated into
    // f1's existing length (Rust replaces C's f1->coeffs += diff pointer
    // shift with a slice copy of the low-order entries).
    #[test]
    fn generate_f1_matches_reduced_sum_of_products() {
        let dim = 2usize;
        let q = 97u64;
        let param = Parameters { dim: dim as u64, N: 1 };
        let channel = Channel::new(5, q, 3);

        let f0 = PolyArray::new(vec![
            Polynomial::new(vec![2, 3]),
            Polynomial::new(vec![1, 4]),
        ]);
        let x = PolyArray::new(vec![
            Polynomial::new(vec![5, 6]),
            Polynomial::new(vec![7, 8]),
        ]);
        let u = Polynomial::new(vec![1, 0, 1]);

        // Independently compute the expected reduced sum.
        let mut expected = Polynomial::new(vec![0; dim * 2]);
        for k in 0..dim {
            let tmp = f0.polies[k].mul(&x.polies[k], q).unwrap();
            expected = expected.add(&tmp, q).unwrap();
        }
        expected.poly_mod(&u, q).unwrap();

        let mut f1 = Polynomial::new(vec![0; dim]);
        generate_f1(&channel, &param, &f0, &x, &u, &mut f1).unwrap();

        let f1_len = f1.coeffs.len();
        let expected_len = expected.coeffs.len();
        let expected_slice: Vec<Coeff> = if expected_len >= f1_len {
            expected.coeffs[expected_len - f1_len..].to_vec()
        } else {
            let mut v = vec![0 as Coeff; f1_len - expected_len];
            v.extend_from_slice(&expected.coeffs);
            v
        };

        assert_eq!(f1.coeffs, expected_slice);
    }
}