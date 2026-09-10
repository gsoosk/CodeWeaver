use rand::Rng;
use std::f64::consts::PI;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Xgcd {
    pub gcd: u64,
    pub a: i64,
    pub b: i64,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Pair {
    pub first: u64,
    pub second: u64,
}
pub fn gcd(mut x: u64, mut y: u64) -> u64 {
    while x != y {
        if x > y {
            x -= y;
        } else {
            y -= x;
        }
    }
    x
}
pub fn xgcd(mut a: u64, mut b: u64) -> Xgcd {
    let mut prev_a: i64 = 1;
    let mut cur_a: i64 = 0;
    let mut prev_b: i64 = 0;
    let mut cur_b: i64 = 1;

    while b != 0 {
        let q = (a / b) as i64;
        let temp_r = (a % b) as i64;
        a = b;
        b = temp_r as u64;

        let temp = cur_a;
        cur_a = prev_a - (q * cur_a);
        prev_a = temp;

        let temp = cur_b;
        cur_b = prev_b - (q * cur_b);
        prev_b = temp;
    }

    Xgcd {
        gcd: a,
        a: prev_a,
        b: prev_b,
    }
}
pub fn are_coprime(x: u64, y: u64) -> bool {
    gcd(x, y) <= 1
}
pub fn randinverse(value: u64) -> Pair {
    let mut a = randrange(2, value - 1);
    while !are_coprime(a, value) {
        a = randrange(2, value - 1);
    }

    let result = xgcd(a, value);

    let second = if result.a > 0 {
        result.a as u64
    } else {
        (result.a + value as i64) as u64
    };

    Pair { first: a, second }
}
pub fn randrange(lower: u64, upper: u64) -> u64 {
    let mut rng = rand::rng();
    rng.random_range(lower..=upper)
}
pub fn normal_rand(mean: f64, stddev: f64) -> f64 {
    let mut rng = rand::rng();

    let mut u: f64 = 0.0;
    while u == 0.0 {
        u = rng.random_range(0.0..=1.0);
    }

    let r = (-2.0 * u.ln()).sqrt();

    let mut theta: f64 = 0.0;
    while theta == 0.0 {
        theta = 2.0 * PI * rng.random_range(0.0..=1.0);
    }

    let x = r * theta.cos();

    (x * stddev) + mean
}
pub fn max(a: u64, b: u64) -> u64 {
    if a > b {
        a
    } else {
        b
    }
}
pub fn min(a: u64, b: u64) -> u64 {
    if a < b {
        a
    } else {
        b
    }
}
pub fn clamp(min_value: u64, max_value: u64, value: u64) -> u64 {
    max(min_value, min(max_value, value))
}

#[cfg(test)]
mod tests {
    use super::*;

    // Direct input->output cases, e.g. gcd(48, 18) == 6 (Euclidean subtraction
    // loop per Common.c).
    #[test]
    fn gcd_matches_known_values() {
        assert_eq!(gcd(48, 18), 6);
        assert_eq!(gcd(17, 5), 1);
        assert_eq!(gcd(100, 100), 100);
        assert_eq!(gcd(270, 192), 6);
    }

    // Bezout identity: gcd == a*x + b*y for the xgcd result.
    #[test]
    fn xgcd_satisfies_bezout_identity() {
        for &(x, y) in &[(48u64, 18u64), (17, 5), (270, 192), (1, 1), (7, 13)] {
            let result = xgcd(x, y);
            assert_eq!(result.gcd, gcd(x, y));
            let computed = result.a as i128 * x as i128 + result.b as i128 * y as i128;
            assert_eq!(computed, result.gcd as i128);
        }
    }

    // are_coprime(x, y) == (gcd(x, y) == 1), boolean equivalence per Common.c.
    #[test]
    fn are_coprime_matches_gcd_equals_one() {
        for &(x, y) in &[(17u64, 5u64), (48, 18), (9, 28), (1, 1), (2, 4)] {
            assert_eq!(are_coprime(x, y), gcd(x, y) == 1);
        }
    }

    // randinverse(value) returns (a, a^-1 mod value) with 1 <= a < value and
    // a * a^-1 == 1 (mod value); property-based (many trials), no exact-value
    // assertion since C's rand() seeding isn't reproduced.
    #[test]
    fn randinverse_produces_valid_modular_inverse() {
        let value: u64 = 97;
        for _ in 0..200 {
            let p = randinverse(value);
            assert!(p.first >= 1 && p.first < value);
            assert!(p.second >= 1 && p.second < value);
            assert_eq!((p.first as u128 * p.second as u128) % value as u128, 1);
        }
    }

    // randrange(lower, upper) is always in the inclusive range [lower, upper]
    // (C: rand() % (upper - lower + 1) + lower).
    #[test]
    fn randrange_stays_within_inclusive_bounds() {
        for _ in 0..200 {
            let v = randrange(5, 10);
            assert!((5..=10).contains(&v));
        }
        // lower == upper edge case
        for _ in 0..20 {
            let v = randrange(7, 7);
            assert_eq!(v, 7);
        }
    }

    // normal_rand invariants only (Box-Muller output isn't reproducible across
    // PRNGs): finite, and repeated sampling doesn't panic.
    #[test]
    fn normal_rand_produces_finite_values() {
        for _ in 0..200 {
            let v = normal_rand(0.0, 1.0);
            assert!(v.is_finite());
        }
    }

    // max/min/clamp exact boundary behavior including equal-args ties.
    #[test]
    fn max_min_clamp_boundary_behavior() {
        assert_eq!(max(3, 7), 7);
        assert_eq!(max(7, 3), 7);
        assert_eq!(max(5, 5), 5);

        assert_eq!(min(3, 7), 3);
        assert_eq!(min(7, 3), 3);
        assert_eq!(min(5, 5), 5);

        assert_eq!(clamp(2, 8, 1), 2); // below range
        assert_eq!(clamp(2, 8, 9), 8); // above range
        assert_eq!(clamp(2, 8, 5), 5); // within range
        assert_eq!(clamp(2, 8, 2), 2); // at min boundary
        assert_eq!(clamp(2, 8, 8), 8); // at max boundary
    }
}