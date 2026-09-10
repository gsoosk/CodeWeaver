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

        if !((p as f64).powi(2) < q as f64 && crate::common::are_coprime(p, q)) {
            channel.q = ((p + 1) as f64).powi(2) as u64;
        }

        Ok(channel)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Channel::init's two branches with concrete values chosen to hit both
    // the "kept as-is" (p^2 < q && coprime(p,q)) and "corrected to (p+1)^2"
    // paths of C's init_channel; both branches return Ok, never Err.
    #[test]
    fn init_keeps_q_when_p_squared_less_than_q_and_coprime() {
        // p = 3, p^2 = 9 < q = 10, gcd(3, 10) = 1 -> coprime, so q is kept.
        let channel = Channel::init(3, 10, 5).unwrap();
        assert_eq!(channel.p, 3);
        assert_eq!(channel.q, 10);
        assert_eq!(channel.w, 5);
    }

    #[test]
    fn init_corrects_q_to_p_plus_one_squared_when_condition_fails() {
        // p = 3, q = 6: p^2 = 9 is not < 6, so condition fails regardless of
        // coprimality; q should become (p+1)^2 = 16.
        let channel = Channel::init(3, 6, 7).unwrap();
        assert_eq!(channel.p, 3);
        assert_eq!(channel.q, 16);
        assert_eq!(channel.w, 7);

        // p = 3, q = 12: p^2 = 9 < 12 holds, but gcd(3, 12) = 3, not coprime,
        // so q should still be corrected to (p+1)^2 = 16.
        let channel = Channel::init(3, 12, 7).unwrap();
        assert_eq!(channel.p, 3);
        assert_eq!(channel.q, 16);
        assert_eq!(channel.w, 7);
    }

    #[test]
    fn new_constructs_unconditionally() {
        let channel = Channel::new(2, 3, 4);
        assert_eq!(channel, Channel { p: 2, q: 3, w: 4 });
    }
}