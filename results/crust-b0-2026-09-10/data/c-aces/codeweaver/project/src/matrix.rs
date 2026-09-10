use crate::common::{randinverse, randrange};
use crate::error::{AcesError, Result};
use rand::Rng;
#[derive(Debug, Clone)]
pub struct Matrix2D {
    pub dim: usize,
    pub data: Vec<u64>,
}
impl Matrix2D {
    pub fn new(dim: usize) -> Self {
        Matrix2D {
            dim,
            data: vec![0u64; dim * dim],
        }
    }
    pub fn row(&self, row: usize) -> Option<&[u64]> {
        if row < self.dim {
            let start = row * self.dim;
            Some(&self.data[start..start + self.dim])
        } else {
            None
        }
    }
    pub fn row_mut(&mut self, row: usize) -> Option<&mut [u64]> {
        if row < self.dim {
            let start = row * self.dim;
            let dim = self.dim;
            Some(&mut self.data[start..start + dim])
        } else {
            None
        }
    }
    pub fn get(&self, row: usize, col: usize) -> Option<u64> {
        if row < self.dim && col < self.dim {
            Some(self.data[row * self.dim + col])
        } else {
            None
        }
    }
    pub fn set(&mut self, row: usize, col: usize, value: u64) -> Result<()> {
        if row < self.dim && col < self.dim {
            let dim = self.dim;
            self.data[row * dim + col] = value;
            Ok(())
        } else {
            Err(AcesError::GenericError(format!(
                "Matrix2D index out of bounds: ({}, {}) for dim {}",
                row, col, self.dim
            )))
        }
    }
}
#[derive(Debug, Clone)]
pub struct Matrix3D {
    pub data: Vec<Matrix2D>,
}
impl Matrix3D {
    pub fn new(size: usize, dim: usize) -> Self {
        Matrix3D {
            data: (0..size).map(|_| Matrix2D::new(dim)).collect(),
        }
    }
    pub fn get_mut(&mut self, idx: usize) -> Option<&mut Matrix2D> {
        self.data.get_mut(idx)
    }
}

fn get_checked(matrix: &Matrix2D, row: usize, col: usize) -> Result<u64> {
    matrix.get(row, col).ok_or_else(|| {
        AcesError::GenericError(format!(
            "Matrix2D index out of bounds: ({}, {}) for dim {}",
            row, col, matrix.dim
        ))
    })
}

pub fn matrix2d_multiply(m: &Matrix2D, invm: &Matrix2D, modulus: u64) -> Result<Matrix2D> {
    let dim = m.dim;
    let mut result = Matrix2D::new(dim);
    for i in 0..dim {
        for j in 0..dim {
            result.set(i, j, 0)?;
            for k in 0..dim {
                let cur = get_checked(&result, i, j)?;
                let a = get_checked(m, i, k)?;
                let b = get_checked(invm, k, j)?;
                result.set(i, j, cur.wrapping_add(a.wrapping_mul(b)))?;
            }
            let cur = get_checked(&result, i, j)?;
            result.set(i, j, cur % modulus)?;
        }
    }

    Ok(result)
}

pub fn swap_transform(m: &mut Matrix2D, invm: &mut Matrix2D, _modulus: u64) -> Result<()> {
    let dim = m.dim;
    let source = randrange(1, (dim - 1) as u64) as usize;
    let target = randrange(0, (source - 1) as u64) as usize;

    for row in 0..dim {
        let tmp = get_checked(m, row, source)?;
        let val = get_checked(m, row, target)?;
        m.set(row, source, val)?;
        m.set(row, target, tmp)?;
    }

    let mut tmp_row = invm
        .row(source)
        .ok_or_else(|| AcesError::GenericError("row out of bounds".to_string()))?
        .to_vec();
    let target_row = invm
        .row(target)
        .ok_or_else(|| AcesError::GenericError("row out of bounds".to_string()))?
        .to_vec();
    invm.row_mut(source)
        .ok_or_else(|| AcesError::GenericError("row out of bounds".to_string()))?
        .copy_from_slice(&target_row);
    invm.row_mut(target)
        .ok_or_else(|| AcesError::GenericError("row out of bounds".to_string()))?
        .copy_from_slice(&tmp_row);
    tmp_row.clear();

    Ok(())
}

pub fn linear_mix_transform(m: &mut Matrix2D, invm: &mut Matrix2D, modulus: u64) -> Result<()> {
    let dim = m.dim;
    let scale = randrange(1, modulus - 1);
    let source = randrange(1, (dim - 1) as u64) as usize;
    let target = randrange(0, (source - 1) as u64) as usize;

    for row in 0..dim {
        let m_target = get_checked(m, row, target)?;
        let m_source = get_checked(m, row, source)?;
        m.set(
            row,
            target,
            (m_target + (m_source as u128 * scale as u128 % modulus as u128) as u64) % modulus,
        )?;

        let invm_source = get_checked(invm, source, row)?;
        let invm_target = get_checked(invm, target, row)?;
        invm.set(
            source,
            row,
            (invm_source
                + (invm_target as u128 * (modulus - scale) as u128 % modulus as u128) as u64)
                % modulus,
        )?;
    }

    Ok(())
}

pub fn scale_transform(m: &mut Matrix2D, invm: &mut Matrix2D, modulus: u64) -> Result<()> {
    let dim = m.dim;
    let scale = randinverse(modulus);
    for idx in 0..dim * dim {
        m.data[idx] = ((m.data[idx] as u128 * scale.first as u128) % modulus as u128) as u64;
        invm.data[idx] =
            ((invm.data[idx] as u128 * scale.second as u128) % modulus as u128) as u64;
    }
    Ok(())
}

pub fn matrix2d_eye(m: &mut Matrix2D) -> Result<()> {
    let dim = m.dim;
    for v in m.data.iter_mut() {
        *v = 0;
    }
    for row in 0..dim {
        m.set(row, row, 1)?;
    }
    Ok(())
}

pub fn fill_random_invertible_pairs(
    m: &mut Matrix2D,
    invm: &mut Matrix2D,
    modulus: u64,
    iterations: usize,
) -> Result<()> {
    const TRANSFORM_COUNT: usize = 3;
    type Transformer = fn(&mut Matrix2D, &mut Matrix2D, u64) -> Result<()>;
    let transformers: [Transformer; TRANSFORM_COUNT] =
        [swap_transform, scale_transform, linear_mix_transform];

    matrix2d_eye(m)?;
    matrix2d_eye(invm)?;

    for _ in 0..iterations {
        let select = randrange(0, (TRANSFORM_COUNT - 1) as u64) as usize;
        transformers[select](m, invm, modulus)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // Matrix2D::get/set/row bounds-respecting accessors return None outside
    // range (Rust adds bounds-checking C's static-inline accessors never had).
    #[test]
    fn matrix2d_accessors_respect_bounds() {
        let mut m = Matrix2D::new(3);
        assert!(m.set(0, 0, 5).is_ok());
        assert_eq!(m.get(0, 0), Some(5));
        assert_eq!(m.get(2, 2), Some(0));
        assert_eq!(m.get(3, 0), None);
        assert_eq!(m.get(0, 3), None);
        assert!(m.set(3, 0, 1).is_err());
        assert!(m.set(0, 3, 1).is_err());
        assert!(m.row(0).is_some());
        assert!(m.row(3).is_none());
        assert!(m.row_mut(2).is_some());
        assert!(m.row_mut(3).is_none());
    }

    // matrix2d_multiply matches a naive triple-loop mod-q product.
    #[test]
    fn matrix2d_multiply_matches_naive_product() {
        let modulus = 97u64;
        let mut m = Matrix2D::new(2);
        m.set(0, 0, 1).unwrap();
        m.set(0, 1, 2).unwrap();
        m.set(1, 0, 3).unwrap();
        m.set(1, 1, 4).unwrap();

        let mut invm = Matrix2D::new(2);
        invm.set(0, 0, 5).unwrap();
        invm.set(0, 1, 6).unwrap();
        invm.set(1, 0, 7).unwrap();
        invm.set(1, 1, 8).unwrap();

        let result = matrix2d_multiply(&m, &invm, modulus).unwrap();

        // naive triple-loop reference computation
        let dim = 2;
        for i in 0..dim {
            for j in 0..dim {
                let mut expected = 0u64;
                for k in 0..dim {
                    expected += m.get(i, k).unwrap() * invm.get(k, j).unwrap();
                }
                expected %= modulus;
                assert_eq!(result.get(i, j).unwrap(), expected);
            }
        }
    }

    // matrix2d_eye produces the identity matrix.
    #[test]
    fn matrix2d_eye_is_identity() {
        let mut m = Matrix2D::new(4);
        // pollute with nonzero values first
        for idx in 0..m.data.len() {
            m.data[idx] = 42;
        }
        matrix2d_eye(&mut m).unwrap();
        for row in 0..4 {
            for col in 0..4 {
                let expected = if row == col { 1 } else { 0 };
                assert_eq!(m.get(row, col).unwrap(), expected);
            }
        }
    }

    fn assert_is_inverse_pair(m: &Matrix2D, invm: &Matrix2D, modulus: u64) {
        let product = matrix2d_multiply(m, invm, modulus).unwrap();
        for row in 0..m.dim {
            for col in 0..m.dim {
                let expected = if row == col { 1 } else { 0 };
                assert_eq!(product.get(row, col).unwrap(), expected);
            }
        }
    }

    // Each transform (swap/linear_mix/scale) preserves the invariant
    // m * invm == I (mod q) before/after application; property-based (many
    // trials), matching Matrix.c's fill_random_invertible_pairs contract.
    #[test]
    fn swap_transform_preserves_inverse_invariant() {
        let modulus = 97u64;
        for _ in 0..50 {
            let mut m = Matrix2D::new(4);
            let mut invm = Matrix2D::new(4);
            matrix2d_eye(&mut m).unwrap();
            matrix2d_eye(&mut invm).unwrap();
            swap_transform(&mut m, &mut invm, modulus).unwrap();
            assert_is_inverse_pair(&m, &invm, modulus);
        }
    }

    #[test]
    fn linear_mix_transform_preserves_inverse_invariant() {
        let modulus = 97u64;
        for _ in 0..50 {
            let mut m = Matrix2D::new(4);
            let mut invm = Matrix2D::new(4);
            matrix2d_eye(&mut m).unwrap();
            matrix2d_eye(&mut invm).unwrap();
            linear_mix_transform(&mut m, &mut invm, modulus).unwrap();
            assert_is_inverse_pair(&m, &invm, modulus);
        }
    }

    #[test]
    fn scale_transform_preserves_inverse_invariant() {
        let modulus = 97u64;
        for _ in 0..50 {
            let mut m = Matrix2D::new(4);
            let mut invm = Matrix2D::new(4);
            matrix2d_eye(&mut m).unwrap();
            matrix2d_eye(&mut invm).unwrap();
            scale_transform(&mut m, &mut invm, modulus).unwrap();
            assert_is_inverse_pair(&m, &invm, modulus);
        }
    }

    // fill_random_invertible_pairs produces a valid invertible pair after N
    // iterations (m * invm == I (mod q)).
    #[test]
    fn fill_random_invertible_pairs_yields_valid_pair() {
        let modulus = 97u64;
        for _ in 0..20 {
            let mut m = Matrix2D::new(5);
            let mut invm = Matrix2D::new(5);
            fill_random_invertible_pairs(&mut m, &mut invm, modulus, 10).unwrap();
            assert_is_inverse_pair(&m, &invm, modulus);
        }
    }
}