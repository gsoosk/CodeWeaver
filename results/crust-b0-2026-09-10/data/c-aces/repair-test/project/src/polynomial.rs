//! Polynomial representation and arithmetic used throughout the crate.

/// The array type used to store polynomial coefficients.
pub type PolyArray = Vec<i64>;

/// A polynomial represented by its coefficients, lowest degree first.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Polynomial {
    pub coeffs: PolyArray,
}

impl Polynomial {
    /// Construct a new polynomial from a coefficient array.
    pub fn new(coeffs: PolyArray) -> Self {
        Polynomial { coeffs }
    }

    /// Construct a zero polynomial with the given number of coefficient slots.
    pub fn zero(len: usize) -> Self {
        Polynomial {
            coeffs: vec![0; len],
        }
    }

    /// Number of coefficients stored.
    pub fn len(&self) -> usize {
        self.coeffs.len()
    }

    pub fn is_empty(&self) -> bool {
        self.coeffs.is_empty()
    }

    /// Degree of the polynomial (highest index with a non-zero coefficient).
    pub fn degree(&self) -> usize {
        for i in (0..self.coeffs.len()).rev() {
            if self.coeffs[i] != 0 {
                return i;
            }
        }
        0
    }

    /// Add two polynomials, returning a new polynomial.
    pub fn add(&self, other: &Polynomial) -> Polynomial {
        let len = self.coeffs.len().max(other.coeffs.len());
        let mut result = vec![0i64; len];
        for i in 0..self.coeffs.len() {
            result[i] = result[i].wrapping_add(self.coeffs[i]);
        }
        for i in 0..other.coeffs.len() {
            result[i] = result[i].wrapping_add(other.coeffs[i]);
        }
        Polynomial::new(result)
    }

    /// Subtract `other` from `self`, returning a new polynomial.
    pub fn sub(&self, other: &Polynomial) -> Polynomial {
        let len = self.coeffs.len().max(other.coeffs.len());
        let mut result = vec![0i64; len];
        for i in 0..self.coeffs.len() {
            result[i] = result[i].wrapping_add(self.coeffs[i]);
        }
        for i in 0..other.coeffs.len() {
            result[i] = result[i].wrapping_sub(other.coeffs[i]);
        }
        Polynomial::new(result)
    }

    /// Multiply two polynomials, returning a new polynomial.
    pub fn mul(&self, other: &Polynomial) -> Polynomial {
        if self.coeffs.is_empty() || other.coeffs.is_empty() {
            return Polynomial::new(Vec::new());
        }
        let len = self.coeffs.len() + other.coeffs.len() - 1;
        let mut result = vec![0i64; len];
        for i in 0..self.coeffs.len() {
            if self.coeffs[i] == 0 {
                continue;
            }
            for j in 0..other.coeffs.len() {
                result[i + j] = result[i + j].wrapping_add(
                    self.coeffs[i].wrapping_mul(other.coeffs[j]),
                );
            }
        }
        Polynomial::new(result)
    }

    /// Evaluate the polynomial at a given point `x`.
    pub fn eval(&self, x: i64) -> i64 {
        let mut result: i64 = 0;
        for &c in self.coeffs.iter().rev() {
            result = result.wrapping_mul(x).wrapping_add(c);
        }
        result
    }

    /// Access the underlying coefficient slice.
    pub fn as_slice(&self) -> &[i64] {
        &self.coeffs
    }

    /// Access the underlying coefficient slice mutably.
    pub fn as_mut_slice(&mut self) -> &mut [i64] {
        &mut self.coeffs
    }
}

impl Default for Polynomial {
    fn default() -> Self {
        Polynomial::new(Vec::new())
    }
}
