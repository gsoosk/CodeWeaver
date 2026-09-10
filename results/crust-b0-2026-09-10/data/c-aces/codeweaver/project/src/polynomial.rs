use crate::error::{AcesError, Result};
pub type Coeff = i64;

/// Reduce a signed coefficient into `[0, modulus)` the way C's Polynomial.c
/// does implicitly: `Coeff % uint64_t` promotes the (int64_t) coefficient to
/// uint64_t (reinterpreting its bit pattern for negative values) before the
/// unsigned modulo, rather than applying signed truncating-toward-zero `%`.
fn reduce_unsigned(value: Coeff, modulus: u64) -> Coeff {
    ((value as u64) % modulus) as Coeff
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Polynomial {
    pub coeffs: Vec<Coeff>,
}
impl Polynomial {
    pub fn new(coeffs: Vec<Coeff>) -> Self {
        Polynomial { coeffs }
    }

    /// Most-significant-first convention: index 0 is the highest degree.
    /// Returns `size - 1 - i` for the first nonzero coefficient, or 0 for an
    /// empty or all-zero polynomial (matches Polynomial.c's `poly_degree`).
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
        if self.coeffs.is_empty() {
            return 0;
        }
        let mut sum: Coeff = 0;
        for c in self.coeffs.iter() {
            sum = sum.wrapping_add(*c);
        }
        sum
    }

    /// Strips the leading (low-index) zero run using `degree()`, then
    /// reduces the remaining coefficients modulo `modulus` (matching
    /// `poly_fit`'s `idx` computation and unsigned-conversion truncation).
    pub fn fit(&mut self, modulus: u64) -> Result<()> {
        if self.coeffs.is_empty() {
            return Err(AcesError::GenericError(
                "fit called on an empty polynomial".to_string(),
            ));
        }

        let degree = self.degree();
        let size = self.coeffs.len();
        let idx = size - 1 - degree;

        let mut i = 0;
        while i + idx < size {
            self.coeffs[i] = reduce_unsigned(self.coeffs[i + idx], modulus);
            i += 1;
        }
        self.coeffs.truncate(size - idx);
        Ok(())
    }

    /// Zero-pads the shorter operand at the low-index end when sizes differ,
    /// then adds coefficient-wise modulo `modulus` (matching `poly_add`).
    pub fn add(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        self.add_or_sub(other, modulus, false)
    }

    /// Same zero-padding rule as `add`, but subtracts (matching `poly_sub`).
    pub fn sub(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        self.add_or_sub(other, modulus, true)
    }

    fn add_or_sub(&self, other: &Polynomial, modulus: u64, is_sub: bool) -> Result<Polynomial> {
        if modulus == 0 {
            return Err(AcesError::GenericError("modulus must be nonzero".to_string()));
        }

        let size = self.coeffs.len().max(other.coeffs.len());
        let diff1 = size - self.coeffs.len();
        let diff2 = size - other.coeffs.len();

        let mut coeffs = vec![0 as Coeff; size];
        for i in 0..size {
            let a = if i >= diff1 { self.coeffs[i - diff1] } else { 0 };
            let b = if i >= diff2 { other.coeffs[i - diff2] } else { 0 };
            let combined = if is_sub {
                (a as u64).wrapping_sub(b as u64)
            } else {
                (a as u64).wrapping_add(b as u64)
            };
            coeffs[i] = (combined % modulus) as Coeff;
        }
        Ok(Polynomial::new(coeffs))
    }

    /// Convolution accumulate then `fit()`, preserving `poly_mul`'s
    /// wrapping multiplication semantics mod `modulus`.
    pub fn mul(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if self.coeffs.is_empty() || other.coeffs.is_empty() {
            return Err(AcesError::GenericError(
                "mul requires non-empty operands".to_string(),
            ));
        }

        let size = self.coeffs.len() + other.coeffs.len() - 1;
        let mut coeffs = vec![0 as Coeff; size];

        for i in 0..self.coeffs.len() {
            for j in 0..other.coeffs.len() {
                let product = self.coeffs[i].wrapping_mul(other.coeffs[j]);
                let reduced = reduce_unsigned(product, modulus);
                coeffs[i + j] = coeffs[i + j].wrapping_add(reduced);
            }
        }

        let mut result = Polynomial::new(coeffs);
        result.fit(modulus)?;
        Ok(result)
    }

    /// Errs when the divisor's leading coefficient isn't 1 or `self`'s
    /// degree is below the divisor's degree; otherwise performs the
    /// per-coefficient subtract-and-correct-sign step and `fit()`s the
    /// result (matching `poly_lshift`).
    pub fn lshift(&self, other: &Polynomial, modulus: u64) -> Result<Polynomial> {
        if other.coeffs.is_empty() || other.coeffs[0] != 1 {
            return Err(AcesError::GenericError(
                "divisor's leading coefficient must be 1".to_string(),
            ));
        }

        let degree1 = self.degree();
        let degree2 = other.degree();
        if degree1 < degree2 {
            return Err(AcesError::GenericError(
                "dividend degree is smaller than divisor degree".to_string(),
            ));
        }

        let a_d = self.coeffs[0];
        let modulus_i = modulus as i64;
        let mut coeffs = vec![0 as Coeff; self.coeffs.len()];
        for i in 0..self.coeffs.len() {
            if i < other.coeffs.len() {
                let diff = self.coeffs[i].wrapping_sub(other.coeffs[i].wrapping_mul(a_d));
                let res = diff.wrapping_rem(modulus_i);
                coeffs[i] = if res < 0 { res.wrapping_add(modulus_i) } else { res };
            } else {
                coeffs[i] = self.coeffs[i];
            }
        }

        let mut result = Polynomial::new(coeffs);
        result.fit(modulus)?;
        Ok(result)
    }

    /// Repeatedly `lshift`s `self` by `divisor` in place until it errs
    /// (self's degree drops below the divisor's), matching `poly_mod`'s
    /// while loop, which always succeeds regardless of the stopping cause.
    pub fn poly_mod(&mut self, divisor: &Polynomial, modulus: u64) -> Result<()> {
        while let Ok(next) = self.lshift(divisor, modulus) {
            *self = next;
        }
        Ok(())
    }

    pub fn sub_scaler(&self, scaler: u64, modulus: u64) -> Result<Polynomial> {
        let coeffs = self
            .coeffs
            .iter()
            .map(|c| ((*c as u64).wrapping_sub(scaler) % modulus) as Coeff)
            .collect();
        Ok(Polynomial::new(coeffs))
    }

    pub fn add_scaler(&self, scaler: u64, modulus: u64) -> Result<Polynomial> {
        let coeffs = self
            .coeffs
            .iter()
            .map(|c| ((*c as u64).wrapping_add(scaler) % modulus) as Coeff)
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

#[cfg(test)]
mod tests {
    use super::*;

    // degree/coef_sum/set_zero/fit exact index/value semantics vs. C,
    // including the MSB-first coefficient convention (index 0 = highest
    // degree) and the "leading (low-index) zero stripping" direction.
    #[test]
    fn degree_matches_msb_first_convention() {
        assert_eq!(Polynomial::new(vec![]).degree(), 0);
        assert_eq!(Polynomial::new(vec![0, 0, 0]).degree(), 0);
        assert_eq!(Polynomial::new(vec![5, 4, 3]).degree(), 2);
        assert_eq!(Polynomial::new(vec![0, 4, 3]).degree(), 1);
        assert_eq!(Polynomial::new(vec![0, 0, 3]).degree(), 0);
    }

    #[test]
    fn coef_sum_matches_hand_computed_example() {
        assert_eq!(Polynomial::new(vec![]).coef_sum(), 0);
        assert_eq!(Polynomial::new(vec![1, 2, 3]).coef_sum(), 6);
        assert_eq!(Polynomial::new(vec![-1, 2, -3]).coef_sum(), -2);
    }

    #[test]
    fn set_zero_zeroes_all_coefficients() {
        let mut p = Polynomial::new(vec![1, 2, 3]);
        p.set_zero();
        assert_eq!(p.coeffs, vec![0, 0, 0]);
    }

    #[test]
    fn fit_strips_leading_zero_coefficients() {
        let mut p = Polynomial::new(vec![0, 0, 5, 12]);
        p.fit(7).unwrap();
        // degree = 1 (index 2 is the first nonzero), idx = 4 - 1 - 1 = 2.
        assert_eq!(p.coeffs, vec![5 % 7, 12 % 7]);

        let mut all_zero = Polynomial::new(vec![0, 0, 0]);
        all_zero.fit(5).unwrap();
        assert_eq!(all_zero.coeffs, vec![0]);

        let mut empty = Polynomial::new(vec![]);
        assert!(empty.fit(5).is_err());
    }

    // add/sub/mul mod-q correctness including the size-mismatch zero-padding
    // logic Polynomial.c implements inline (poly_add/poly_sub).
    #[test]
    fn add_matches_hand_computed_example() {
        let a = Polynomial::new(vec![3, 4]);
        let b = Polynomial::new(vec![5, 6]);
        let result = a.add(&b, 7).unwrap();
        assert_eq!(result.coeffs, vec![(3 + 5) % 7, (4 + 6) % 7]);

        // size mismatch: zero-pad the shorter operand at the low-index end.
        let short = Polynomial::new(vec![1]);
        let long = Polynomial::new(vec![2, 3, 4]);
        let result = short.add(&long, 5).unwrap();
        assert_eq!(result.coeffs, vec![2 % 5, 3 % 5, (1 + 4) % 5]);

        assert!(a.add(&b, 0).is_err());
    }

    #[test]
    fn sub_matches_hand_computed_example() {
        let a = Polynomial::new(vec![3, 4]);
        let b = Polynomial::new(vec![5, 6]);
        let result = a.sub(&b, 7).unwrap();
        assert_eq!(
            result.coeffs,
            vec![
                ((3i64 as u64).wrapping_sub(5) % 7) as Coeff,
                ((4i64 as u64).wrapping_sub(6) % 7) as Coeff,
            ]
        );

        assert!(a.sub(&b, 0).is_err());
    }

    #[test]
    fn mul_matches_hand_computed_example() {
        // (x + 2)(x + 3) = x^2 + 5x + 6, MSB-first: [1, 2] * [1, 3].
        let a = Polynomial::new(vec![1, 2]);
        let b = Polynomial::new(vec![1, 3]);
        let result = a.mul(&b, 100).unwrap();
        assert_eq!(result.coeffs, vec![1, 5, 6]);

        let mod_result = a.mul(&b, 4).unwrap();
        assert_eq!(mod_result.coeffs, vec![1, 1, 2]);
    }

    // lshift/poly_mod replicate C's Euclidean-style polynomial reduction;
    // divisor's leading coefficient must be 1, else Err (poly_lshift).
    #[test]
    fn lshift_errs_when_divisor_leading_coeff_is_not_one() {
        let dividend = Polynomial::new(vec![1, 0, 0]);
        let bad_divisor = Polynomial::new(vec![2, 1]);
        assert!(dividend.lshift(&bad_divisor, 7).is_err());

        // Also errs when the dividend's degree is below the divisor's.
        let low_degree = Polynomial::new(vec![1]);
        let divisor = Polynomial::new(vec![1, 0]);
        assert!(low_degree.lshift(&divisor, 7).is_err());
    }

    #[test]
    fn poly_mod_reduces_below_divisor_degree() {
        // x^3 mod (x^2 + 1), over Z_7.
        let mut p = Polynomial::new(vec![1, 0, 0, 0]);
        let divisor = Polynomial::new(vec![1, 0, 1]);
        p.poly_mod(&divisor, 7).unwrap();
        assert!(p.degree() < divisor.degree());
    }

    // sub_scaler/add_scaler per-coefficient mod arithmetic.
    #[test]
    fn sub_scaler_applies_to_every_coefficient() {
        let p = Polynomial::new(vec![10, 20, 30]);
        let result = p.sub_scaler(3, 7).unwrap();
        let expected: Vec<Coeff> = p
            .coeffs
            .iter()
            .map(|c| ((*c as u64).wrapping_sub(3) % 7) as Coeff)
            .collect();
        assert_eq!(result.coeffs, expected);
    }

    #[test]
    fn add_scaler_applies_to_every_coefficient() {
        let p = Polynomial::new(vec![10, 20, 30]);
        let result = p.add_scaler(3, 7).unwrap();
        let expected: Vec<Coeff> = p
            .coeffs
            .iter()
            .map(|c| ((*c as u64).wrapping_add(3) % 7) as Coeff)
            .collect();
        assert_eq!(result.coeffs, expected);
    }
}