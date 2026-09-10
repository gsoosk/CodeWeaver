use crate::error::{AcesError, Result};
pub type Coeff = i64;
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Polynomial {
    pub coeffs: Vec<Coeff>,
}
impl Polynomial {
    pub fn new(coeffs: Vec<Coeff>) -> Self {
        Polynomial { coeffs }
    }
    pub fn degree(&self) -> usize {
        if self.coeffs.is_empty() {
            return 0;
        }
        for (i, c) in self.coeffs.iter().enumerate() {
            if *c != 0 {
                return self.coeffs.len() - i - 1;
            }
        }
        0
    }
    pub fn set_zero(&mut self) {
        for c in self.coeffs.iter_mut() {
            *c = 0;
        }
    }
    pub fn coef_sum(&self) -> Coeff {
        self.coeffs.iter().fold(0i64, |acc, &c| acc.wrapping_add(c))
    }
    pub fn fit(&mut self, modulus: u64) -> Result<()> {
        if self.coeffs.is_empty() {
            return Err(AcesError::GenericError("empty polynomial".into()));
        }
        let degree = self.degree();
        let len = self.coeffs.len();
        let idx = len - 1 - degree;
        for i in 0..(len - idx) {
            let v = self.coeffs[i + idx] as u64;
            self.coeffs[i] = (v % modulus) as i64;
        }
        self.coeffs.truncate(len - idx);
        Ok(())
    }
    pub fn add(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if modulus == 0 {
            return Err(AcesError::GenericError("modulus is zero".into()));
        }
        let size = self.coeffs.len().max(other.coeffs.len());
        let diff1 = size - self.coeffs.len();
        let diff2 = size - other.coeffs.len();
        let mut result = vec![0i64; size];
        for i in 0..size {
            let v1 = if i >= diff1 { self.coeffs[i - diff1] } else { 0 };
            let v2 = if i >= diff2 { other.coeffs[i - diff2] } else { 0 };
            let sum = v1.wrapping_add(v2) as u64;
            result[i] = (sum % modulus) as i64;
        }
        Ok(Polynomial { coeffs: result })
    }
    pub fn sub(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if modulus == 0 {
            return Err(AcesError::GenericError("modulus is zero".into()));
        }
        let size = self.coeffs.len().max(other.coeffs.len());
        let diff1 = size - self.coeffs.len();
        let diff2 = size - other.coeffs.len();
        let mut result = vec![0i64; size];
        for i in 0..size {
            let v1 = if i >= diff1 { self.coeffs[i - diff1] } else { 0 };
            let v2 = if i >= diff2 { other.coeffs[i - diff2] } else { 0 };
            let diff = v1.wrapping_sub(v2) as u64;
            result[i] = (diff % modulus) as i64;
        }
        Ok(Polynomial { coeffs: result })
    }
    pub fn mul(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if self.coeffs.is_empty() || other.coeffs.is_empty() {
            return Err(AcesError::GenericError("empty polynomial".into()));
        }
        let deg1 = self.coeffs.len() - 1;
        let deg2 = other.coeffs.len() - 1;
        let size = deg1 + deg2 + 1;
        let mut result = vec![0i64; size];
        let modi = modulus as i128;
        for i in 0..self.coeffs.len() {
            for j in 0..other.coeffs.len() {
                let term = ((self.coeffs[i] as i128) * (other.coeffs[j] as i128)).rem_euclid(modi);
                result[i + j] = result[i + j].wrapping_add(term as i64);
            }
        }
        let mut p = Polynomial { coeffs: result };
        p.fit(modulus)?;
        Ok(p)
    }
    pub fn lshift(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if other.coeffs.is_empty() || other.coeffs[0] != 1 {
            return Err(AcesError::GenericError("invalid divisor".into()));
        }
        let degree1 = self.degree();
        let degree2 = other.degree();
        if degree1 < degree2 {
            return Err(AcesError::GenericError("degree1 < degree2".into()));
        }
        let a_d = self.coeffs[0];
        let mut result = vec![0i64; self.coeffs.len()];
        for i in 0..self.coeffs.len() {
            if i < other.coeffs.len() {
                let res = (self.coeffs[i] as i128 - other.coeffs[i] as i128 * a_d as i128)
                    % modulus as i128;
                result[i] = if res < 0 {
                    (res + modulus as i128) as i64
                } else {
                    res as i64
                };
            } else {
                result[i] = self.coeffs[i];
            }
        }
        let mut p = Polynomial { coeffs: result };
        p.fit(modulus)?;
        Ok(p)
    }
    pub fn poly_mod(&mut self, divisor: &Polynomial, modulus: u64) -> Result<()> {
        loop {
            match self.lshift(divisor, modulus) {
                Ok(p) => {
                    *self = p;
                }
                Err(_) => break,
            }
        }
        Ok(())
    }
    pub fn sub_scaler(&self, scaler: u64, modulus: u64) -> Result<Polynomial> {
        let mut result = vec![0i64; self.coeffs.len()];
        for i in 0..self.coeffs.len() {
            let v = (self.coeffs[i] as u64).wrapping_sub(scaler);
            result[i] = (v % modulus) as i64;
        }
        Ok(Polynomial { coeffs: result })
    }
    pub fn add_scaler(&self, scaler: u64, modulus: u64) -> Result<Polynomial> {
        let mut result = vec![0i64; self.coeffs.len()];
        for i in 0..self.coeffs.len() {
            let v = (self.coeffs[i] as u64).wrapping_add(scaler);
            result[i] = (v % modulus) as i64;
        }
        Ok(Polynomial { coeffs: result })
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PolyArray {
    pub polies: Vec<Polynomial>,
}
impl PolyArray {
    pub fn new(polies: Vec<Polynomial>) -> Self {
        PolyArray { polies }
    }
}
