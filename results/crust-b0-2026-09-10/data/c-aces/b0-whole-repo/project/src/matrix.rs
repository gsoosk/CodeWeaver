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
            return Err(AcesError::GenericError("matrix index out of bounds".into()));
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
        Matrix3D {
            data: (0..size).map(|_| Matrix2D::new(dim)).collect(),
        }
    }
    pub fn get_mut(&mut self, idx: usize) -> Option<&mut Matrix2D> {
        self.data.get_mut(idx)
    }
}
pub fn matrix2d_multiply(m: &Matrix2D, invm: &Matrix2D, modulus: u64) -> Result<Matrix2D> {
    if modulus == 0 {
        return Err(AcesError::GenericError("modulus is zero".into()));
    }
    let dim = m.dim;
    let mut result = Matrix2D::new(dim);
    for i in 0..dim {
        for j in 0..dim {
            let mut acc: u128 = 0;
            for k in 0..dim {
                let mv = m.get(i, k).ok_or_else(|| AcesError::GenericError("idx".into()))? as u128;
                let iv = invm
                    .get(k, j)
                    .ok_or_else(|| AcesError::GenericError("idx".into()))? as u128;
                acc = acc.wrapping_add(mv.wrapping_mul(iv));
            }
            result.set(i, j, (acc % modulus as u128) as u64)?;
        }
    }
    Ok(result)
}
pub fn swap_transform(m: &mut Matrix2D, invm: &mut Matrix2D, _modulus: u64) -> Result<()> {
    let dim = m.dim;
    if dim < 2 {
        return Err(AcesError::GenericError("dim too small".into()));
    }
    let source = randrange(1, (dim - 1) as u64) as usize;
    let target = randrange(0, source.saturating_sub(1) as u64) as usize;

    for row in 0..dim {
        let v_source = m
            .get(row, source)
            .ok_or_else(|| AcesError::GenericError("idx".into()))?;
        let v_target = m
            .get(row, target)
            .ok_or_else(|| AcesError::GenericError("idx".into()))?;
        m.set(row, source, v_target)?;
        m.set(row, target, v_source)?;
    }

    let row_source: Vec<u64> = invm
        .row(source)
        .ok_or_else(|| AcesError::GenericError("idx".into()))?
        .to_vec();
    let row_target: Vec<u64> = invm
        .row(target)
        .ok_or_else(|| AcesError::GenericError("idx".into()))?
        .to_vec();
    invm.row_mut(source)
        .ok_or_else(|| AcesError::GenericError("idx".into()))?
        .copy_from_slice(&row_target);
    invm.row_mut(target)
        .ok_or_else(|| AcesError::GenericError("idx".into()))?
        .copy_from_slice(&row_source);

    Ok(())
}
pub fn linear_mix_transform(m: &mut Matrix2D, invm: &mut Matrix2D, modulus: u64) -> Result<()> {
    let dim = m.dim;
    if dim < 2 || modulus < 2 {
        return Err(AcesError::GenericError("invalid parameters".into()));
    }
    let scale = randrange(1, modulus - 1);
    let source = randrange(1, (dim - 1) as u64) as usize;
    let target = randrange(0, source.saturating_sub(1) as u64) as usize;

    for row in 0..dim {
        let m_target = m
            .get(row, target)
            .ok_or_else(|| AcesError::GenericError("idx".into()))? as u128;
        let m_source = m
            .get(row, source)
            .ok_or_else(|| AcesError::GenericError("idx".into()))? as u128;
        let newval = (m_target + m_source * scale as u128) % modulus as u128;
        m.set(row, target, newval as u64)?;

        let inv_source = invm
            .get(source, row)
            .ok_or_else(|| AcesError::GenericError("idx".into()))? as u128;
        let inv_target = invm
            .get(target, row)
            .ok_or_else(|| AcesError::GenericError("idx".into()))? as u128;
        let factor = (modulus - scale) as u128;
        let newinv = (inv_source + inv_target * factor) % modulus as u128;
        invm.set(source, row, newinv as u64)?;
    }

    Ok(())
}
pub fn scale_transform(m: &mut Matrix2D, invm: &mut Matrix2D, modulus: u64) -> Result<()> {
    let dim = m.dim;
    let pair = randinverse(modulus);
    for idx in 0..dim * dim {
        m.data[idx] = ((m.data[idx] as u128 * pair.first as u128) % modulus as u128) as u64;
        invm.data[idx] = ((invm.data[idx] as u128 * pair.second as u128) % modulus as u128) as u64;
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
    matrix2d_eye(m)?;
    matrix2d_eye(invm)?;

    for _ in 0..iterations {
        let select = randrange(0, 2);
        match select {
            0 => swap_transform(m, invm, modulus)?,
            1 => scale_transform(m, invm, modulus)?,
            _ => linear_mix_transform(m, invm, modulus)?,
        }
    }
    Ok(())
}
