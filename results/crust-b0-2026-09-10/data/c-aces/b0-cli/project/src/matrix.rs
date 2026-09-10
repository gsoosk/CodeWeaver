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
            self.data[row * self.dim + col] = value;
            Ok(())
        } else {
            Err(AcesError::GenericError(
                "matrix index out of bounds".to_string(),
            ))
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

pub fn matrix2d_multiply(m: &Matrix2D, invm: &Matrix2D, modulus: u64) -> Result<Matrix2D> {
    if m.dim != invm.dim {
        return Err(AcesError::GenericError(
            "matrix dimension mismatch".to_string(),
        ));
    }

    let dim = m.dim;
    let mut result = Matrix2D::new(dim);

    for i in 0..dim {
        for j in 0..dim {
            let mut sum: u64 = 0;
            for k in 0..dim {
                let a = m.get(i, k).unwrap();
                let b = invm.get(k, j).unwrap();
                sum = sum.wrapping_add(a.wrapping_mul(b));
            }
            result.set(i, j, sum % modulus)?;
        }
    }

    Ok(result)
}

pub fn swap_transform(m: &mut Matrix2D, invm: &mut Matrix2D, _modulus: u64) -> Result<()> {
    let dim = m.dim;
    let source = randrange(1, (dim as u64).saturating_sub(1)) as usize;
    let target = randrange(0, (source as u64).saturating_sub(1)) as usize;

    for row in 0..dim {
        let a = m.get(row, source).unwrap();
        let b = m.get(row, target).unwrap();
        m.set(row, source, b)?;
        m.set(row, target, a)?;
    }

    let source_row = invm.row(source).unwrap().to_vec();
    let target_row = invm.row(target).unwrap().to_vec();
    invm.row_mut(source).unwrap().copy_from_slice(&target_row);
    invm.row_mut(target).unwrap().copy_from_slice(&source_row);

    Ok(())
}

pub fn linear_mix_transform(m: &mut Matrix2D, invm: &mut Matrix2D, modulus: u64) -> Result<()> {
    let dim = m.dim;
    let scale = randrange(1, modulus.saturating_sub(1));
    let source = randrange(1, (dim as u64).saturating_sub(1)) as usize;
    let target = randrange(0, (source as u64).saturating_sub(1)) as usize;

    for row in 0..dim {
        let mt = m.get(row, target).unwrap();
        let ms = m.get(row, source).unwrap();
        let new_val = (mt.wrapping_add(ms.wrapping_mul(scale))) % modulus;
        m.set(row, target, new_val)?;

        let inv_s = invm.get(source, row).unwrap();
        let inv_t = invm.get(target, row).unwrap();
        let new_inv = (inv_s.wrapping_add(inv_t.wrapping_mul(modulus - scale))) % modulus;
        invm.set(source, row, new_inv)?;
    }

    Ok(())
}

pub fn scale_transform(m: &mut Matrix2D, invm: &mut Matrix2D, modulus: u64) -> Result<()> {
    let scale = randinverse(modulus);

    for v in m.data.iter_mut() {
        *v = (v.wrapping_mul(scale.first)) % modulus;
    }
    for v in invm.data.iter_mut() {
        *v = (v.wrapping_mul(scale.second)) % modulus;
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
    let transformers: [fn(&mut Matrix2D, &mut Matrix2D, u64) -> Result<()>; 3] =
        [swap_transform, scale_transform, linear_mix_transform];

    matrix2d_eye(m)?;
    matrix2d_eye(invm)?;

    for _ in 0..iterations {
        let select = randrange(0, 2) as usize;
        transformers[select](m, invm, modulus)?;
    }

    Ok(())
}
