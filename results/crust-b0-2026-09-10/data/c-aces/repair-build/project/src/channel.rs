use crate::error::{AcesError, Result};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Parameters {
    pub dim: u64,
    pub N: u64,
}

/// Represents an arithmetic channel.
///
/// An arithmetic channel consists of a tuple (p, q, ω, u) where:
/// 1) p, q, and ω are positive integers such that p < q;
/// 2) u is a polynomial in Z[X] such that u(ω) = q.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Channel {
    pub p: u64,
    pub q: u64,
    pub w: u64,
}

fn gcd(a: u64, b: u64) -> u64 {
    if b == 0 {
        a
    } else {
        gcd(b, a % b)
    }
}

fn are_coprime(a: u64, b: u64) -> bool {
    gcd(a, b) == 1
}

impl Channel {
    /// Creates a new channel.
    pub fn new(p: u64, q: u64, w: u64) -> Self {
        Channel { p, q, w }
    }

    /// Initializes a channel and checks that `p < q`.
    pub fn init(p: u64, q: u64, w: u64) -> Result<Self> {
        let mut final_q = q;

        if !(p.saturating_pow(2) < q && are_coprime(p, q)) {
            final_q = (p + 1).saturating_pow(2);
        }

        Ok(Channel { p, q: final_q, w })
    }
}
