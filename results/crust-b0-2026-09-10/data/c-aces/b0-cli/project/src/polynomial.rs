use crate::error::{AcesError, Result};

pub type Coeff = i64;

fn mod_coeff(x: i64, modulus: u64) -> i64 {
    ((x as u64) % modulus) as i64
}

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

        for i in 0..self.coeffs.len() {
            if self.coeffs[i] != 0 {
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
        self.coeffs.iter().fold(0i64, |acc, &x| acc.wrapping_add(x))
    }

    pub fn fit(&mut self, modulus: u64) -> Result<()> {
        if self.coeffs.is_empty() {
            return Err(AcesError::GenericError("empty polynomial".to_string()));
        }

        let degree = self.degree();
        let idx = self.coeffs.len() - 1 - degree;

        let mut new_coeffs = Vec::with_capacity(self.coeffs.len() - idx);
        for i in idx..self.coeffs.len() {
            new_coeffs.push(mod_coeff(self.coeffs[i], modulus));
        }
        self.coeffs = new_coeffs;

        Ok(())
    }

    pub fn add(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if modulus == 0 {
            return Err(AcesError::GenericError("modulus is zero".to_string()));
        }

        let size = self.coeffs.len().max(other.coeffs.len());
        let diff1 = size - self.coeffs.len();
        let diff2 = size - other.coeffs.len();

        let mut coeffs = vec![0i64; size];
        for i in 0..size {
            let a = if i >= diff1 { self.coeffs[i - diff1] } else { 0 };
            let b = if i >= diff2 { other.coeffs[i - diff2] } else { 0 };
            coeffs[i] = mod_coeff(a.wrapping_add(b), modulus);
        }

        Ok(Polynomial::new(coeffs))
    }

    pub fn sub(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if modulus == 0 {
            return Err(AcesError::GenericError("modulus is zero".to_string()));
        }

        let size = self.coeffs.len().max(other.coeffs.len());
        let diff1 = size - self.coeffs.len();
        let diff2 = size - other.coeffs.len();

        let mut coeffs = vec![0i64; size];
        for i in 0..size {
            let a = if i >= diff1 { self.coeffs[i - diff1] } else { 0 };
            let b = if i >= diff2 { other.coeffs[i - diff2] } else { 0 };
            coeffs[i] = mod_coeff(a.wrapping_sub(b), modulus);
        }

        Ok(Polynomial::new(coeffs))
    }

    pub fn mul(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        let deg1 = self.coeffs.len().saturating_sub(1);
        let deg2 = other.coeffs.len().saturating_sub(1);
        let size = deg1 + deg2 + 1;

        let mut coeffs = vec![0i64; size];
        for i in 0..self.coeffs.len() {
            for j in 0..other.coeffs.len() {
                let prod = mod_coeff(self.coeffs[i].wrapping_mul(other.coeffs[j]), modulus);
                coeffs[i + j] = coeffs[i + j].wrapping_add(prod);
            }
        }

        let mut result = Polynomial::new(coeffs);
        result.fit(modulus)?;
        Ok(result)
    }

    pub fn lshift(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if other.coeffs.is_empty() || other.coeffs[0] != 1 {
            return Err(AcesError::GenericError("invalid divisor".to_string()));
        }

        let degree1 = self.degree();
        let degree2 = other.degree();

        if degree1 < degree2 {
            return Err(AcesError::GenericError(
                "degree of poly1 less than degree of poly2".to_string(),
            ));
        }

        let a_d = self.coeffs[0];
        let modi = modulus as i64;

        let mut coeffs = vec![0i64; self.coeffs.len()];
        for i in 0..self.coeffs.len() {
            if i < other.coeffs.len() {
                let res = (self.coeffs[i].wrapping_sub(other.coeffs[i].wrapping_mul(a_d))) % modi;
                coeffs[i] = if res < 0 { res + modi } else { res };
            } else {
                coeffs[i] = self.coeffs[i];
            }
        }

        let mut result = Polynomial::new(coeffs);
        result.fit(modulus)?;
        Ok(result)
    }

    pub fn poly_mod(&mut self, divisor: &Polynomial, modulus: u64) -> Result<()> {
        loop {
            match self.lshift(divisor, modulus) {
                Ok(r) => {
                    *self = r;
                }
                Err(_) => break,
            }
        }
        Ok(())
    }

    pub fn sub_scaler(&self, scaler: u64, modulus: u64) -> Result<Polynomial> {
        let coeffs: Vec<i64> = self
            .coeffs
            .iter()
            .map(|&c| (((c as u64).wrapping_sub(scaler)) % modulus) as i64)
            .collect();
        Ok(Polynomial::new(coeffs))
    }

    pub fn add_scaler(&self, scaler: u64, modulus: u64) -> Result<Polynomial> {
        let coeffs: Vec<i64> = self
            .coeffs
            .iter()
            .map(|&c| (((c as u64).wrapping_add(scaler)) % modulus) as i64)
            .collect();
        Ok(Polynomial::new(coeffs))
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
