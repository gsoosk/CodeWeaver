use std::fmt;

#[derive(Debug)]
pub enum InversionListError {
    ValueOutOfRange(u32, u32),
    Generic(String),
}

#[derive(Clone, Debug)]
pub struct InversionList {
    capacity: u32,
    support: u32,
    pub intervals: Vec<(u32, u32)>,
}

fn union_intervals(a: &[(u32, u32)], b: &[(u32, u32)]) -> Vec<(u32, u32)> {
    let mut all: Vec<(u32, u32)> = a.iter().cloned().chain(b.iter().cloned()).collect();
    all.sort_unstable();
    let mut result: Vec<(u32, u32)> = Vec::new();
    for (s, e) in all {
        if let Some(last) = result.last_mut() {
            if s <= last.1 {
                if e > last.1 {
                    last.1 = e;
                }
                continue;
            }
        }
        result.push((s, e));
    }
    result
}

fn intersect_intervals(a: &[(u32, u32)], b: &[(u32, u32)]) -> Vec<(u32, u32)> {
    let mut result = Vec::new();
    let (mut i, mut j) = (0usize, 0usize);
    while i < a.len() && j < b.len() {
        let (as_, ae) = a[i];
        let (bs, be) = b[j];
        let s = as_.max(bs);
        let e = ae.min(be);
        if s < e {
            result.push((s, e));
        }
        if ae < be {
            i += 1;
        } else if ae > be {
            j += 1;
        } else {
            i += 1;
            j += 1;
        }
    }
    result
}

fn difference_intervals(a: &[(u32, u32)], b: &[(u32, u32)]) -> Vec<(u32, u32)> {
    let mut result = Vec::new();
    for &(s, e) in a {
        let mut cur = s;
        for &(bs, be) in b {
            if be <= cur || bs >= e {
                continue;
            }
            if bs > cur {
                result.push((cur, bs.min(e)));
            }
            if be > cur {
                cur = be;
            }
            if cur >= e {
                break;
            }
        }
        if cur < e {
            result.push((cur, e));
        }
    }
    result
}

fn support_of(intervals: &[(u32, u32)]) -> u32 {
    intervals.iter().map(|&(s, e)| e - s).sum()
}

impl InversionList {
    pub fn new(capacity: u32, values: &[u32]) -> Result<Self, InversionListError> {
        let mut vals: Vec<u32> = values.to_vec();
        vals.sort_unstable();
        vals.dedup();

        if let Some(&max) = vals.last() {
            if max >= capacity {
                return Err(InversionListError::ValueOutOfRange(max, capacity));
            }
        }

        let support = vals.len() as u32;
        let mut intervals: Vec<(u32, u32)> = Vec::new();
        for v in vals {
            if let Some(last) = intervals.last_mut() {
                if v == last.1 {
                    last.1 = v + 1;
                    continue;
                }
            }
            intervals.push((v, v + 1));
        }

        Ok(InversionList {
            capacity,
            support,
            intervals,
        })
    }

    pub fn capacity(&self) -> u32 {
        self.capacity
    }

    pub fn support(&self) -> u32 {
        self.support
    }

    pub fn contains(&self, value: u32) -> bool {
        self.intervals.iter().any(|&(s, e)| value >= s && value < e)
    }

    pub fn clone_list(&self) -> Self {
        self.clone()
    }

    pub fn complement(&self) -> Self {
        let mut intervals = Vec::new();
        let mut prev = 0u32;
        for &(s, e) in &self.intervals {
            if s > prev {
                intervals.push((prev, s));
            }
            prev = e;
        }
        if prev < self.capacity {
            intervals.push((prev, self.capacity));
        }

        InversionList {
            capacity: self.capacity,
            support: self.capacity - self.support,
            intervals,
        }
    }

    pub fn to_str(&self) -> String {
        let mut s = String::from("[");
        let mut first = true;
        for &(lo, hi) in &self.intervals {
            for v in lo..hi {
                if first {
                    first = false;
                } else {
                    s.push_str(", ");
                }
                s.push_str(&v.to_string());
            }
        }
        s.push(']');
        s
    }

    pub fn equal(&self, other: &Self) -> bool {
        self.support == other.support && self.intervals == other.intervals
    }

    pub fn is_strict_subset_of(&self, other: &Self) -> bool {
        if self.support >= other.support {
            return false;
        }
        let last = match self.intervals.last() {
            Some(&(_, e)) => e,
            None => return false,
        };
        let mut i = 0u32;
        while i < last {
            if other.contains(i) {
                return true;
            }
            i += 1;
        }
        false
    }

    pub fn is_subset_of(&self, other: &Self) -> bool {
        self.equal(other) || self.is_strict_subset_of(other)
    }

    pub fn is_disjoint(&self, other: &Self) -> bool {
        !self.equal(other)
    }

    pub fn union(&self, other: &Self) -> Self {
        let capacity = self.capacity.max(other.capacity);
        let intervals = union_intervals(&self.intervals, &other.intervals);
        let support = support_of(&intervals);
        InversionList {
            capacity,
            support,
            intervals,
        }
    }

    pub fn intersection(&self, other: &Self) -> Self {
        let capacity = self.capacity.max(other.capacity);
        let intervals = intersect_intervals(&self.intervals, &other.intervals);
        let support = support_of(&intervals);
        InversionList {
            capacity,
            support,
            intervals,
        }
    }

    pub fn difference(&self, other: &Self) -> Self {
        let capacity = self.capacity.max(other.capacity);
        let intervals = difference_intervals(&self.intervals, &other.intervals);
        let support = support_of(&intervals);
        InversionList {
            capacity,
            support,
            intervals,
        }
    }

    pub fn symmetric_difference(&self, other: &Self) -> Self {
        let u = self.union(other);
        let i = self.intersection(other);
        u.difference(&i)
    }
}

impl PartialEq for InversionList {
    fn eq(&self, other: &Self) -> bool {
        self.equal(other)
    }
}

impl Eq for InversionList {}

impl fmt::Display for InversionList {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.to_str())
    }
}

pub struct InversionListIterator<'a> {
    list: &'a InversionList,
    interval_index: usize,
    current_value: u32,
}

impl<'a> InversionListIterator<'a> {
    pub fn new(list: &'a InversionList) -> Self {
        let current_value = list.intervals.first().map(|&(s, _)| s).unwrap_or(0);
        InversionListIterator {
            list,
            interval_index: 0,
            current_value,
        }
    }
}

impl<'a> Iterator for InversionListIterator<'a> {
    type Item = u32;
    fn next(&mut self) -> Option<Self::Item> {
        loop {
            if self.interval_index >= self.list.intervals.len() {
                return None;
            }
            let (s, e) = self.list.intervals[self.interval_index];
            if self.current_value < s {
                self.current_value = s;
            }
            if self.current_value >= e {
                self.interval_index += 1;
                if self.interval_index < self.list.intervals.len() {
                    self.current_value = self.list.intervals[self.interval_index].0;
                }
                continue;
            }
            let val = self.current_value;
            self.current_value += 1;
            return Some(val);
        }
    }
}

pub struct InversionListCoupleIterator<'a> {
    list: &'a InversionList,
    couple_index: usize,
}

impl<'a> InversionListCoupleIterator<'a> {
    pub fn new(list: &'a InversionList) -> Self {
        InversionListCoupleIterator {
            list,
            couple_index: 0,
        }
    }
}

impl<'a> Iterator for InversionListCoupleIterator<'a> {
    type Item = (u32, u32);
    fn next(&mut self) -> Option<Self::Item> {
        if self.couple_index < self.list.intervals.len() {
            let c = self.list.intervals[self.couple_index];
            self.couple_index += 1;
            Some(c)
        } else {
            None
        }
    }
}
