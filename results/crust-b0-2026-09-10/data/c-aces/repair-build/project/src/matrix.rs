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
        if row >= self.dim {
            return None;
        }
        let start = row * self.dim;
        Some(&self.data[start..start + self.dim])
    }

    pub fn row_mut(&mut self, row: usize) -> Option<&mut [u64]> {
        if row >= self.dim {
            return None;
        }
        let start = row * self.dim;
        let dim = self.dim;
        Some(&mut self.data[start..start + dim])
    }

    pub fn get(&self, row: usize, col: usize) -> Option<u64> {
        if row >= self.dim || col >= self.dim {
            return None;
        }
        Some(self.data[row * self.dim + col])
    }

    pub fn set(&mut self, row: usize, col: usize, value: u64) -> Result<()> {
        if row >= self.dim || col >= self.dim {
            return Err(AcesError::Other(format!(
                "matrix index out of bounds: ({}, {})",
                row, col
            )));
        }
        let dim = self.dim;
        self.data[row * dim + col] = value;
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct Matrix3D {
    pub data: Vec<Matrix2D>,
}

impl Matrix3D {
    pub fn new(size: usize, dim: usize) -> Self {
        let mut data = Vec::with_capacity(size);
        for _ in 0..size {
            data.push(Matrix2D::new(dim));
        }
        Matrix3D { data }
    }

    pub fn get_mut(&mut self, idx: usize) -> Option<&mut Matrix2D> {
        self.data.get_mut(idx)
    }
}

pub fn matrix2d_multiply(m: &Matrix2D, invm: &Matrix2D, modulus: u64) -> Result<Matrix2D> {
    let dim = m.dim;
    let mut result = Matrix2D::new(dim);

    for i in 0..dim {
        for j in 0..dim {
            let mut acc: u128 = 0;
            for k in 0..dim {
                let mv = m
                    .get(i, k)
                    .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
                    as u128;
                let iv = invm
                    .get(k, j)
                    .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
                    as u128;
                acc += mv * iv;
            }
            let value = (acc % modulus as u128) as u64;
            result.set(i, j, value)?;
        }
    }

    Ok(result)
}

pub fn swap_transform(m: &mut Matrix2D, invm: &mut Matrix2D, _modulus: u64) -> Result<()> {
    let dim = m.dim;

    let source = randrange(1, dim - 1);
    let target = randrange(0, source - 1);

    for row in 0..dim {
        let a = m
            .get(row, source)
            .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?;
        let b = m
            .get(row, target)
            .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?;
        m.set(row, source, b)?;
        m.set(row, target, a)?;
    }

    let tmp_row: Vec<u64> = invm
        .row(source)
        .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
        .to_vec();
    let target_row: Vec<u64> = invm
        .row(target)
        .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
        .to_vec();

    invm.row_mut(source)
        .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
        .copy_from_slice(&target_row);
    invm.row_mut(target)
        .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
        .copy_from_slice(&tmp_row);

    Ok(())
}

pub fn linear_mix_transform(m: &mut Matrix2D, invm: &mut Matrix2D, modulus: u64) -> Result<()> {
    let dim = m.dim;
    let scale = randrange(1, (modulus - 1) as usize) as u64;
    let source = randrange(1, dim - 1);
    let target = randrange(0, source - 1);

    for row in 0..dim {
        let m_target = m
            .get(row, target)
            .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
            as u128;
        let m_source = m
            .get(row, source)
            .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
            as u128;
        let new_val = ((m_target + m_source * scale as u128) % modulus as u128) as u64;
        m.set(row, target, new_val)?;

        let inv_source = invm
            .get(source, row)
            .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
            as u128;
        let inv_target = invm
            .get(target, row)
            .ok_or_else(|| AcesError::Other("index out of bounds".to_string()))?
            as u128;
        let neg_scale = (modulus - scale) as u128;
        let new_inv = ((inv_source + inv_target * neg_scale) % modulus as u128) as u64;
        invm.set(source, row, new_inv)?;
    }

    Ok(())
}

pub fn scale_transform(m: &mut Matrix2D, invm: &mut Matrix2D, modulus: u64) -> Result<()> {
    let (scale1, scale2) = randinverse(modulus);

    for idx in 0..m.data.len() {
        let v = m.data[idx] as u128;
        m.data[idx] = ((v * scale1 as u128) % modulus as u128) as u64;
    }

    for idx in 0..invm.data.len() {
        let v = invm.data[idx] as u128;
        invm.data[idx] = ((v * scale2 as u128) % modulus as u128) as u64;
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

const TRANSFORM_COUNT: usize = 3;

pub fn fill_random_invertible_pairs(
    m: &mut Matrix2D,
    invm: &mut Matrix2D,
    modulus: u64,
    iterations: usize,
) -> Result<()> {
    matrix2d_eye(m)?;
    matrix2d_eye(invm)?;

    for _ in 0..iterations {
        let select = randrange(0, TRANSFORM_COUNT - 1);
        match select {
            0 => swap_transform(m, invm, modulus)?,
            1 => scale_transform(m, invm, modulus)?,
            2 => linear_mix_transform(m, invm, modulus)?,
            _ => unreachable!(),
        }
    }

    Ok(())
}
