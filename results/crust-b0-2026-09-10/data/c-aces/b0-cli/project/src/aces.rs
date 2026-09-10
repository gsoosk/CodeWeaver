use crate::aces_internal::{
    generate_error, generate_f0, generate_f1, generate_linear, generate_secret, generate_u,
    generate_vanisher,
};
use crate::channel::{Channel, Parameters};
use crate::error::{AcesError, Result};
use crate::matrix::Matrix3D;
use crate::polynomial::{PolyArray, Polynomial};

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
pub fn set_aces(aces: &mut Aces, dim: usize, mem: &mut [u8]) -> Result<()> {
    let required = std::mem::size_of::<i64>() * (2 * dim + 1 + 2 * dim * dim)
        + std::mem::size_of::<crate::matrix::Matrix2D>() * dim
        + std::mem::size_of::<Polynomial>() * 2 * dim
        + std::mem::size_of::<u64>() * dim * dim * dim;

    if mem.len() < required {
        return Err(AcesError::GenericError("insufficient memory".to_string()));
    }

    aces.shared_info.pk.u = Polynomial::new(vec![0i64; dim + 1]);
    aces.shared_info.pk.lambda = Matrix3D::new(dim, dim);

    aces.private_key.x =
        PolyArray::new((0..dim).map(|_| Polynomial::new(vec![0i64; dim])).collect());
    aces.private_key.f0 =
        PolyArray::new((0..dim).map(|_| Polynomial::new(vec![0i64; dim])).collect());
    aces.private_key.f1 = Polynomial::new(vec![0i64; dim]);

    Ok(())
}

/// Initialize an instance of ACES.
pub fn init_aces(p: u64, q: u64, dim: u64, aces: &mut Aces) -> Result<()> {
    aces.shared_info.param.dim = dim;
    aces.shared_info.param.N = 1;
    aces.shared_info.channel = Channel::init(p, q, 1)?;

    let dim_usize = dim as usize;
    aces.shared_info.pk.u = Polynomial::new(vec![0i64; dim_usize + 1]);
    aces.shared_info.pk.lambda = Matrix3D::new(dim_usize, dim_usize);
    aces.private_key.x = PolyArray::new(
        (0..dim_usize)
            .map(|_| Polynomial::new(vec![0i64; dim_usize]))
            .collect(),
    );
    aces.private_key.f0 = PolyArray::new(
        (0..dim_usize)
            .map(|_| Polynomial::new(vec![0i64; dim_usize]))
            .collect(),
    );
    aces.private_key.f1 = Polynomial::new(vec![0i64; dim_usize]);

    generate_u(
        &aces.shared_info.channel,
        &aces.shared_info.param,
        &mut aces.shared_info.pk.u,
    )?;

    let u = aces.shared_info.pk.u.clone();
    let channel = aces.shared_info.channel;
    let param = aces.shared_info.param;

    generate_secret(
        &channel,
        &param,
        &u,
        &mut aces.private_key.x,
        &mut aces.shared_info.pk.lambda,
    )?;

    generate_f0(&channel, &param, &mut aces.private_key.f0)?;

    let f0 = aces.private_key.f0.clone();
    let x = aces.private_key.x.clone();

    generate_f1(&channel, &param, &f0, &x, &u, &mut aces.private_key.f1)?;

    Ok(())
}

/// Encrypt a message.
pub fn aces_encrypt(aces: &Aces, message: &[u64], result: &mut CipherMessage) -> Result<()> {
    if message.len() > 1 {
        return Err(AcesError::GenericError(
            "message size too large".to_string(),
        ));
    }

    let msg = *message
        .get(0)
        .ok_or_else(|| AcesError::GenericError("message required".to_string()))?;

    let dim = aces.shared_info.param.dim as usize;
    let q = aces.shared_info.channel.q;
    let p = aces.shared_info.channel.p;

    let mut r_m = Polynomial::new(vec![0i64; dim]);
    generate_error(q, msg, &mut r_m)?;

    let mut e = Polynomial::new(vec![0i64; dim]);
    generate_vanisher(p, q, &mut e)?;

    let mut b = Polynomial::new(vec![0i64; dim]);
    generate_linear(p, q, &mut b)?;

    // C1
    for i in 0..dim {
        let mut tmp = b.mul(&aces.private_key.f0.polies[i], q)?;
        tmp.poly_mod(&aces.shared_info.pk.u, q)?;
        result.c1.polies[i] = tmp;
    }

    // C2
    let c2_pre = aces.private_key.f1.add(&e, q)?;
    let mut tmp = c2_pre.mul(&b, q)?;
    tmp = tmp.add(&r_m, q)?;
    tmp.poly_mod(&aces.shared_info.pk.u, q)?;
    result.c2 = tmp;

    // Level
    result.level = p;

    Ok(())
}

/// Decrypt a ciphertext.
pub fn aces_decrypt(aces: &Aces, message: &CipherMessage, result: &mut [u64]) -> Result<()> {
    let dim = aces.shared_info.param.dim as usize;
    let q = aces.shared_info.channel.q;
    let p = aces.shared_info.channel.p;

    let mut c0tx = Polynomial::new(vec![0i64; 2 * dim]);
    for i in 0..dim {
        let tmp = message.c1.polies[i].mul(&aces.private_key.x.polies[i], q)?;
        c0tx = tmp.add(&c0tx, q)?;
    }

    c0tx.fit(q)?;
    let c0tx = message.c2.sub(&c0tx, q)?;

    let sum = c0tx.coef_sum();
    let val = ((sum as u64) % q) % p;

    let out = result
        .get_mut(0)
        .ok_or_else(|| AcesError::GenericError("result buffer empty".to_string()))?;
    *out = val;

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

    for i in 0..dim {
        let mut sum = a.c1.polies[i].add(&b.c1.polies[i], info.channel.q)?;
        sum.poly_mod(&info.pk.u, info.channel.q)?;
        result.c1.polies[i] = sum;
    }

    let mut c2 = a.c2.add(&b.c2, info.channel.q)?;
    c2.poly_mod(&info.pk.u, info.channel.q)?;
    result.c2 = c2;

    result.level = a.level.wrapping_add(b.level);

    Ok(())
}

/// Perform homomorphic multiplication on two ciphertexts.
pub fn aces_mul(
    _a: &CipherMessage,
    _b: &CipherMessage,
    _info: &SharedInfo,
    _result: &mut CipherMessage,
) -> Result<()> {
    // Not implemented upstream (TODO in original C source).
    Ok(())
}

/// Refresh a ciphertext to mitigate level increase.
pub fn aces_refresh(info: &SharedInfo, message: &mut CipherMessage, level: u64) -> Result<()> {
    let scaler = level.wrapping_mul(info.channel.p);
    let new_c2 = message.c2.sub_scaler(scaler, info.channel.q)?;
    message.c2 = new_c2;
    message.level = message.level.wrapping_sub(level);
    Ok(())
}
