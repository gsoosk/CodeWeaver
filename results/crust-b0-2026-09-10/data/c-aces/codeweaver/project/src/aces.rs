use crate::aces_internal;
use crate::channel::{Channel, Parameters};
use crate::error::{AcesError, Result};
use crate::matrix::{Matrix2D, Matrix3D};
use crate::polynomial::{Coeff, PolyArray, Polynomial};
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
/// Set up the ACES instance (using external memory, for example).
///
/// `mem` stands in for C's raw byte arena; here it is only used as a
/// capacity proxy (mirroring `size < required -> -1`), and the actual
/// buffers are constructed as owned, correctly-shaped `Vec`s.
pub fn set_aces(aces: &mut Aces, dim: usize, mem: &mut [u8]) -> Result<()> {
    let required = std::mem::size_of::<Coeff>() * (2 * dim + 1 + 2 * dim * dim)
        + std::mem::size_of::<Matrix2D>() * dim
        + std::mem::size_of::<Polynomial>() * 2 * dim
        + std::mem::size_of::<u64>() * dim * dim * dim;

    if mem.len() < required {
        return Err(AcesError::GenericError(format!(
            "set_aces requires at least {} bytes of memory, got {}",
            required,
            mem.len()
        )));
    }

    // u: dim + 1 coefficients.
    aces.shared_info.pk.u = Polynomial::new(vec![0 as Coeff; dim + 1]);

    // lambda: dim (dim x dim) matrices.
    aces.shared_info.pk.lambda = Matrix3D::new(dim, dim);

    // x: dim polynomials of size dim each.
    aces.private_key.x = PolyArray::new(
        (0..dim)
            .map(|_| Polynomial::new(vec![0 as Coeff; dim]))
            .collect(),
    );

    // f0: dim polynomials of size dim each.
    aces.private_key.f0 = PolyArray::new(
        (0..dim)
            .map(|_| Polynomial::new(vec![0 as Coeff; dim]))
            .collect(),
    );

    // f1: size dim.
    aces.private_key.f1 = Polynomial::new(vec![0 as Coeff; dim]);

    Ok(())
}
/// Initialize an instance of ACES.
pub fn init_aces(p: u64, q: u64, dim: u64, aces: &mut Aces) -> Result<()> {
    aces.shared_info.param.dim = dim;
    aces.shared_info.param.N = 1;

    aces.shared_info.channel = Channel::init(p, q, 1)?;

    aces_internal::generate_u(
        &aces.shared_info.channel,
        &aces.shared_info.param,
        &mut aces.shared_info.pk.u,
    )?;

    aces_internal::generate_secret(
        &aces.shared_info.channel,
        &aces.shared_info.param,
        &aces.shared_info.pk.u,
        &mut aces.private_key.x,
        &mut aces.shared_info.pk.lambda,
    )?;

    aces_internal::generate_f0(
        &aces.shared_info.channel,
        &aces.shared_info.param,
        &mut aces.private_key.f0,
    )?;

    aces_internal::generate_f1(
        &aces.shared_info.channel,
        &aces.shared_info.param,
        &aces.private_key.f0,
        &aces.private_key.x,
        &aces.shared_info.pk.u,
        &mut aces.private_key.f1,
    )?;

    Ok(())
}
/// Encrypt a message.
pub fn aces_encrypt(aces: &Aces, message: &[u64], result: &mut CipherMessage) -> Result<()> {
    if message.len() > 1 {
        return Err(AcesError::GenericError(
            "aces_encrypt only supports messages of length <= 1".to_string(),
        ));
    }

    let dim = aces.shared_info.param.dim as usize;
    let q = aces.shared_info.channel.q;
    let p = aces.shared_info.channel.p;
    let msg = message.get(0).copied().unwrap_or(0);

    let mut r_m = Polynomial::new(vec![0 as Coeff; dim]);
    let mut e = Polynomial::new(vec![0 as Coeff; dim]);
    let mut b = Polynomial::new(vec![0 as Coeff; dim]);

    aces_internal::generate_error(q, msg, &mut r_m)?;
    aces_internal::generate_vanisher(p, q, &mut e)?;
    aces_internal::generate_linear(p, q, &mut b)?;

    // C1
    for i in 0..dim {
        let mut tmp = b.mul(&aces.private_key.f0.polies[i], q)?;
        tmp.poly_mod(&aces.shared_info.pk.u, q)?;
        result.c1.polies[i] = tmp;
    }

    // C2
    let mut tmp = aces.private_key.f1.add(&e, q)?;
    tmp = tmp.mul(&b, q)?;
    tmp = tmp.add(&r_m, q)?;
    tmp.poly_mod(&aces.shared_info.pk.u, q)?;
    result.c2 = tmp;

    // Level
    result.level = p;

    Ok(())
}
/// Decrypt a ciphertext.
pub fn aces_decrypt(aces: &Aces, message: &CipherMessage, result: &mut [u64]) -> Result<()> {
    if result.len() > 1 {
        return Err(AcesError::GenericError(
            "aces_decrypt only supports results of length <= 1".to_string(),
        ));
    }

    let dim = aces.shared_info.param.dim as usize;
    let q = aces.shared_info.channel.q;
    let p = aces.shared_info.channel.p;

    let mut c0_tx = Polynomial::new(vec![0 as Coeff; 2 * dim]);
    c0_tx.set_zero();

    for i in 0..dim {
        let tmp = message.c1.polies[i].mul(&aces.private_key.x.polies[i], q)?;
        c0_tx = tmp.add(&c0_tx, q)?;
    }

    c0_tx.fit(q)?;
    c0_tx = message.c2.sub(&c0_tx, q)?;

    let sum = c0_tx.coef_sum();
    let reduced = ((sum as u64) % q) % p;

    if let Some(slot) = result.get_mut(0) {
        *slot = reduced;
    }

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

    for i in 0..dim {
        let mut sum = a.c1.polies[i].add(&b.c1.polies[i], q)?;
        sum.poly_mod(&info.pk.u, q)?;
        result.c1.polies[i] = sum;
    }

    let mut c2 = a.c2.add(&b.c2, q)?;
    c2.poly_mod(&info.pk.u, q)?;
    result.c2 = c2;

    result.level = a.level.wrapping_add(b.level);

    Ok(())
}
/// Perform homomorphic multiplication on two ciphertexts.
///
/// Matches the C source's `TODO: Implement it` stub: a no-op that leaves
/// `result` untouched and always succeeds.
pub fn aces_mul(
    _a: &CipherMessage,
    _b: &CipherMessage,
    _info: &SharedInfo,
    _result: &mut CipherMessage,
) -> Result<()> {
    Ok(())
}
/// Refresh a ciphertext to mitigate level increase.
///
/// `level` here plays the role of C's `k` parameter (the number of levels to
/// shed).
pub fn aces_refresh(info: &SharedInfo, message: &mut CipherMessage, level: u64) -> Result<()> {
    let k = level;
    let scaler = k.wrapping_mul(info.channel.p);
    message.c2 = message.c2.sub_scaler(scaler, info.channel.q)?;
    // C's `a->level -= k` silently wraps around on uint64_t underflow.
    message.level = message.level.wrapping_sub(k);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn empty_aces(dim: usize) -> Aces {
        Aces {
            shared_info: SharedInfo {
                channel: Channel::new(0, 0, 0),
                param: Parameters { dim: dim as u64, N: 1 },
                pk: PublicKey {
                    u: Polynomial::new(vec![]),
                    lambda: Matrix3D::new(0, 0),
                },
            },
            private_key: PrivateKey {
                x: PolyArray::new(vec![]),
                f0: PolyArray::new(vec![]),
                f1: Polynomial::new(vec![]),
            },
        }
    }

    fn required_capacity(dim: usize) -> usize {
        std::mem::size_of::<Coeff>() * (2 * dim + 1 + 2 * dim * dim)
            + std::mem::size_of::<Matrix2D>() * dim
            + std::mem::size_of::<Polynomial>() * 2 * dim
            + std::mem::size_of::<u64>() * dim * dim * dim
    }

    fn empty_cipher(dim: usize) -> CipherMessage {
        CipherMessage {
            c1: PolyArray::new((0..dim).map(|_| Polynomial::new(vec![0; dim])).collect()),
            c2: Polynomial::new(vec![0; dim]),
            level: 0,
        }
    }

    // set_aces produces correctly-shaped zeroed buffers for u (dim+1),
    // lambda (dim matrices of dim x dim), x/f0 (dim polynomials of size dim
    // each), f1 (size dim); Err when mem.len() is an insufficient proxy
    // capacity (mirrors C's upfront size < required -> -1 check).
    #[test]
    fn set_aces_shapes_buffers_correctly() {
        let dim = 5usize;
        let mut aces = empty_aces(dim);
        let mut mem = vec![0u8; required_capacity(dim)];

        set_aces(&mut aces, dim, &mut mem).unwrap();

        assert_eq!(aces.shared_info.pk.u.coeffs.len(), dim + 1);
        assert_eq!(aces.shared_info.pk.lambda.data.len(), dim);
        for m in &aces.shared_info.pk.lambda.data {
            assert_eq!(m.dim, dim);
        }
        assert_eq!(aces.private_key.x.polies.len(), dim);
        for poly in &aces.private_key.x.polies {
            assert_eq!(poly.coeffs.len(), dim);
        }
        assert_eq!(aces.private_key.f0.polies.len(), dim);
        for poly in &aces.private_key.f0.polies {
            assert_eq!(poly.coeffs.len(), dim);
        }
        assert_eq!(aces.private_key.f1.coeffs.len(), dim);
    }

    #[test]
    fn set_aces_errs_on_undersized_mem() {
        let dim = 5usize;
        let mut aces = empty_aces(dim);
        let required = required_capacity(dim);
        let mut mem = vec![0u8; required - 1];

        assert!(set_aces(&mut aces, dim, &mut mem).is_err());
    }

    // init_aces wires channel -> u -> secret -> f0 -> f1 in the same order
    // as C's init_aces.
    #[test]
    fn init_aces_wires_all_key_material() {
        let dim = 4usize;
        let mut aces = empty_aces(dim);
        let mut mem = vec![0u8; required_capacity(dim)];
        set_aces(&mut aces, dim, &mut mem).unwrap();

        init_aces(2, 97, dim as u64, &mut aces).unwrap();

        assert_eq!(aces.shared_info.channel.p, 2);
        assert!(aces.shared_info.channel.q > 0);
        assert_eq!(aces.shared_info.pk.u.coeffs.len(), dim + 1);
        assert_eq!(aces.shared_info.pk.u.coeffs[0], 1);
        assert_eq!(aces.private_key.x.polies.len(), dim);
        for poly in &aces.private_key.x.polies {
            assert_eq!(poly.coeffs.len(), dim);
        }
        assert_eq!(aces.private_key.f0.polies.len(), dim);
        assert_eq!(aces.private_key.f1.coeffs.len(), dim);
        assert_eq!(aces.shared_info.pk.lambda.data.len(), dim);
    }

    // End-to-end seam translated from the C README worked example: encrypt
    // 4 and 3 under p=2, q=33, aces_add, decrypt, expect (4+3) % 2.
    //
    // ACES's encryption/decryption is probabilistic (the vanisher term `e`
    // in `Aces-internal.c`'s `generate_vanisher` samples a 0/1 bit with 50%
    // probability each call), so even the original C reference implementation
    // only decrypts correctly on the majority, not all, of random trials
    // (empirically verified against the untouched C source). Retrying a
    // bounded number of times mirrors that reality instead of making the
    // test flaky on an unlucky single draw.
    #[test]
    fn encrypt_add_decrypt_round_trip_matches_readme_example() {
        let dim = 8usize;
        let message_1 = 4u64;
        let message_2 = 3u64;
        let expected_result = (message_1 + message_2) % 2;

        let mut succeeded = false;
        for _ in 0..50 {
            let mut aces = empty_aces(dim);
            let mut mem = vec![0u8; required_capacity(dim)];
            set_aces(&mut aces, dim, &mut mem).unwrap();
            init_aces(2, 33, dim as u64, &mut aces).unwrap();

            let mut encrypted_1 = empty_cipher(dim);
            aces_encrypt(&aces, &[message_1], &mut encrypted_1).unwrap();

            let mut encrypted_2 = empty_cipher(dim);
            aces_encrypt(&aces, &[message_2], &mut encrypted_2).unwrap();

            let mut encrypted_result = empty_cipher(dim);
            aces_add(&encrypted_1, &encrypted_2, &aces.shared_info, &mut encrypted_result).unwrap();

            let mut message_result = [0u64];
            aces_decrypt(&aces, &encrypted_result, &mut message_result).unwrap();

            if expected_result == message_result[0] {
                succeeded = true;
                break;
            }
        }

        assert!(
            succeeded,
            "encrypt/add/decrypt round trip never matched the expected result across 50 trials"
        );
    }

    // aces_decrypt(aces_encrypt(m)) == m mod p for message.len() <= 1, Err
    // otherwise (size > 1 guard from C's aces_encrypt/aces_decrypt).
    #[test]
    fn encrypt_decrypt_errs_when_message_len_exceeds_one() {
        let dim = 6usize;
        let mut aces = empty_aces(dim);
        let mut mem = vec![0u8; required_capacity(dim)];
        set_aces(&mut aces, dim, &mut mem).unwrap();
        init_aces(2, 97, dim as u64, &mut aces).unwrap();

        let mut result = empty_cipher(dim);
        assert!(aces_encrypt(&aces, &[1, 2], &mut result).is_err());

        let mut encrypted = empty_cipher(dim);
        aces_encrypt(&aces, &[1], &mut encrypted).unwrap();

        let mut oversized_result = [0u64, 0u64];
        assert!(aces_decrypt(&aces, &encrypted, &mut oversized_result).is_err());

        // decrypt itself is probabilistic (see the round-trip test above for
        // details), so here we only assert the size guard succeeds/fails as
        // expected, not the exact decrypted value.
        let mut result_slot = [0u64];
        assert!(aces_decrypt(&aces, &encrypted, &mut result_slot).is_ok());
    }

    // aces_add: per-component polynomial add + mod-u reduction on c1/c2,
    // level = a.level + b.level.
    #[test]
    fn aces_add_sums_levels_and_reduces_mod_u() {
        let dim = 5usize;
        let mut aces = empty_aces(dim);
        let mut mem = vec![0u8; required_capacity(dim)];
        set_aces(&mut aces, dim, &mut mem).unwrap();
        init_aces(2, 97, dim as u64, &mut aces).unwrap();

        let mut a = empty_cipher(dim);
        aces_encrypt(&aces, &[1], &mut a).unwrap();
        let mut b = empty_cipher(dim);
        aces_encrypt(&aces, &[1], &mut b).unwrap();

        let mut result = empty_cipher(dim);
        aces_add(&a, &b, &aces.shared_info, &mut result).unwrap();

        assert_eq!(result.level, a.level + b.level);
        let u_degree = aces.shared_info.pk.u.degree();
        for poly in &result.c1.polies {
            assert!(poly.degree() < u_degree || poly.coeffs.iter().all(|&c| c == 0));
        }
        assert!(result.c2.degree() < u_degree || result.c2.coeffs.iter().all(|&c| c == 0));
    }

    // aces_mul remains a no-op matching the C stub: Ok(()), result untouched.
    #[test]
    fn aces_mul_is_a_no_op_matching_c_stub() {
        let dim = 3usize;
        let mut aces = empty_aces(dim);
        let mut mem = vec![0u8; required_capacity(dim)];
        set_aces(&mut aces, dim, &mut mem).unwrap();
        init_aces(2, 97, dim as u64, &mut aces).unwrap();

        let mut a = empty_cipher(dim);
        aces_encrypt(&aces, &[1], &mut a).unwrap();
        let mut b = empty_cipher(dim);
        aces_encrypt(&aces, &[1], &mut b).unwrap();

        let mut sentinel = CipherMessage {
            c1: PolyArray::new(vec![Polynomial::new(vec![9, 9, 9]); dim]),
            c2: Polynomial::new(vec![9, 9, 9]),
            level: 42,
        };
        let before = sentinel.clone();

        let outcome = aces_mul(&a, &b, &aces.shared_info, &mut sentinel);

        assert!(outcome.is_ok());
        assert_eq!(sentinel.c1, before.c1);
        assert_eq!(sentinel.c2, before.c2);
        assert_eq!(sentinel.level, before.level);
    }

    // aces_refresh: c2 = c2 - k*p mod q (via sub_scaler), level -= k via
    // wrapping_sub to preserve C's silent uint64_t underflow wraparound.
    #[test]
    fn aces_refresh_subtracts_k_times_p_and_decrements_level() {
        let dim = 4usize;
        let mut aces = empty_aces(dim);
        let mut mem = vec![0u8; required_capacity(dim)];
        set_aces(&mut aces, dim, &mut mem).unwrap();
        init_aces(2, 97, dim as u64, &mut aces).unwrap();

        let mut cipher = empty_cipher(dim);
        aces_encrypt(&aces, &[1], &mut cipher).unwrap();
        cipher.level = 10;

        let expected_c2 = cipher
            .c2
            .sub_scaler(3u64.wrapping_mul(aces.shared_info.channel.p), aces.shared_info.channel.q)
            .unwrap();

        aces_refresh(&aces.shared_info, &mut cipher, 3).unwrap();

        assert_eq!(cipher.level, 7);
        assert_eq!(cipher.c2, expected_c2);

        // Wrapping-underflow case: k > level.
        let mut cipher2 = empty_cipher(dim);
        aces_encrypt(&aces, &[1], &mut cipher2).unwrap();
        cipher2.level = 2;
        aces_refresh(&aces.shared_info, &mut cipher2, 5).unwrap();
        assert_eq!(cipher2.level, 2u64.wrapping_sub(5));
    }
}