use crate::error::Result;

pub type Coeff = i64;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Polynomial {
    pub coeffs: Vec<Coeff>,
}

impl Polynomial {
    pub fn new(coeffs: Vec<Coeff>) -> Self {
        Polynomial { coeffs }
    }

    /// Compute the degree of the polynomial, mirroring `poly_degree` in the
    /// original C implementation. The "degree" here is computed as
    /// `size - i - 1` for the first non-zero coefficient found scanning from
    /// the most-significant term (index 0).
    pub fn degree(&self) -> usize {
        let size = self.coeffs.len();
        if size == 0 {
            return 0;
        }

        for (i, &c) in self.coeffs.iter().enumerate() {
            if c != 0 {
                return size - i - 1;
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
        if self.coeffs.is_empty() {
            return 0;
        }
        self.coeffs.iter().sum()
    }

    /// Fit the polynomial to the given modulus and strip leading zero
    /// coefficients, mirroring `poly_fit`.
    pub fn fit(&mut self, modulus: u64) -> Result<()> {
        if self.coeffs.is_empty() {
            return Err(format!("cannot fit an empty polynomial").into());
        }

        let size = self.coeffs.len();
        let degree = self.degree();
        let idx = size - 1 - degree;
        let m = modulus as i64;

        let mut new_coeffs = Vec::with_capacity(size - idx);
        for i in idx..size {
            new_coeffs.push(self.coeffs[i] % m);
        }

        self.coeffs = new_coeffs;
        Ok(())
    }

    pub fn add(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if modulus == 0 {
            return Err(format!("modulus cannot be zero").into());
        }

        let size = self.coeffs.len().max(other.coeffs.len());
        let diff1 = size - self.coeffs.len();
        let diff2 = size - other.coeffs.len();
        let m = modulus as i64;

        let mut coeffs = vec![0i64; size];
        for i in 0..size {
            let a = if i >= diff1 { self.coeffs[i - diff1] } else { 0 };
            let b = if i >= diff2 { other.coeffs[i - diff2] } else { 0 };
            coeffs[i] = (a + b) % m;
        }

        Ok(Polynomial { coeffs })
    }

    pub fn sub(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if modulus == 0 {
            return Err(format!("modulus cannot be zero").into());
        }

        let size = self.coeffs.len().max(other.coeffs.len());
        let diff1 = size - self.coeffs.len();
        let diff2 = size - other.coeffs.len();
        let m = modulus as i64;

        let mut coeffs = vec![0i64; size];
        for i in 0..size {
            let a = if i >= diff1 { self.coeffs[i - diff1] } else { 0 };
            let b = if i >= diff2 { other.coeffs[i - diff2] } else { 0 };
            coeffs[i] = (a - b) % m;
        }

        Ok(Polynomial { coeffs })
    }

    pub fn mul(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        let len1 = self.coeffs.len();
        let len2 = other.coeffs.len();

        if len1 == 0 || len2 == 0 {
            return Err(format!("cannot multiply an empty polynomial").into());
        }

        let size = len1 + len2 - 1;
        let m = modulus as i64;

        let mut coeffs = vec![0i64; size];
        for i in 0..len1 {
            for j in 0..len2 {
                coeffs[i + j] = (coeffs[i + j] + (self.coeffs[i] * other.coeffs[j]) % m) % m;
            }
        }

        let mut result = Polynomial { coeffs };
        result.fit(modulus)?;
        Ok(result)
    }

    pub fn lshift(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if other.coeffs.is_empty() || other.coeffs[0] != 1 {
            return Err(format!("leading coefficient of divisor must be 1").into());
        }

        let degree1 = self.degree();
        let degree2 = other.degree();

        if degree1 < degree2 {
            return Err(format!("degree of dividend must be >= degree of divisor").into());
        }

        let a_d = self.coeffs[0];
        let m = modulus as i64;

        let mut coeffs = vec![0i64; self.coeffs.len()];
        for i in 0..self.coeffs.len() {
            if i < other.coeffs.len() {
                let res = (self.coeffs[i] - other.coeffs[i] * a_d) % m;
                coeffs[i] = if res < 0 { res + m } else { res };
            } else {
                coeffs[i] = self.coeffs[i];
            }
        }

        let mut result = Polynomial { coeffs };
        result.fit(modulus)?;
        Ok(result)
    }

    pub fn poly_mod(&mut self, divisor: &Polynomial, modulus: u64) -> Result<()> {
        loop {
            match self.lshift(divisor, modulus) {
                Ok(new_poly) => {
                    *self = new_poly;
                }
                Err(_) => break,
            }
        }
        Ok(())
    }

    pub fn sub_scaler(&self, scaler: u64, modulus: u64) -> Result<Polynomial> {
        let m = modulus as i64;
        let s = scaler as i64;

        let coeffs = self.coeffs.iter().map(|&c| (c - s) % m).collect();
        Ok(Polynomial { coeffs })
    }

    pub fn add_scaler(&self, scaler: u64, modulus: u64) -> Result<Polynomial> {
        let m = modulus as i64;
        let s = scaler as i64;

        let coeffs = self.coeffs.iter().map(|&c| (c + s) % m).collect();
        Ok(Polynomial { coeffs })
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
