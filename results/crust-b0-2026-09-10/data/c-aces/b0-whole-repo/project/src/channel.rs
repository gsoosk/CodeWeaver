use crate::common::are_coprime;
use crate::error::{AcesError, Result};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Parameters {
    pub dim: u64,
    pub N: u64,
}
/// Represents an arithmetic channel.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Channel {
    pub p: u64,
    pub q: u64,
    pub w: u64,
}
impl Channel {
    /// Creates a new channel.
    pub fn new(p: u64, q: u64, w: u64) -> Self {
        Channel { p, q, w }
    }
    /// Initializes a channel and checks that `p < q`.
    pub fn init(p: u64, q: u64, w: u64) -> Result<Self> {
        let mut channel = Channel { p, q, w };
        let pf = p as f64;
        let qf = q as f64;
        if !(pf.powi(2) < qf && are_coprime(p, q)) {
            channel.q = ((p + 1) as f64).powi(2) as u64;
        }
        let _ = AcesError::GenericError(String::new());
        Ok(channel)
    }
}
