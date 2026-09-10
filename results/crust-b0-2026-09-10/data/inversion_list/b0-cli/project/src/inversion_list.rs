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
    let mut all: Vec<(u32, u32)> = Vec::with_capacity(a.len() + b.len());
    all.extend_from_slice(a);
    all.extend_from_slice(b);
    all.sort_by_key(|&(s, _)| s);

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

fn intersection_intervals(a: &[(u32, u32)], b: &[(u32, u32)]) -> Vec<(u32, u32)> {
    let mut result = Vec::new();
    let mut i = 0usize;
    let mut j = 0usize;
    while i < a.len() && j < b.len() {
        let (a_s, a_e) = a[i];
        let (b_s, b_e) = b[j];
        let start = a_s.max(b_s);
        let end = a_e.min(b_e);
        if start < end {
            result.push((start, end));
        }
        if a_e < b_e {
            i += 1;
        } else if a_e > b_e {
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
    let mut j = 0usize;
    for &(a_s, a_e) in a {
        let mut cur = a_s;
        while j < b.len() && b[j].1 <= cur {
            j += 1;
        }
        let mut k = j;
        while cur < a_e {
            if k < b.len() {
                let (b_s, b_e) = b[k];
                if b_e <= cur {
                    k += 1;
                    continue;
                }
                if b_s >= a_e {
                    // no more overlap in this interval
                    result.push((cur, a_e));
                    cur = a_e;
                    break;
                }
                if b_s > cur {
                    result.push((cur, b_s));
                }
                cur = b_e.max(cur);
                if cur < a_e {
                    k += 1;
                }
            } else {
                result.push((cur, a_e));
                cur = a_e;
            }
        }
    }
    result
}

fn support_of(intervals: &[(u32, u32)]) -> u32 {
    intervals.iter().map(|&(s, e)| e - s).sum()
}

impl InversionList {
    pub fn new(capacity: u32, values: &[u32]) -> Result<Self, InversionListError> {
        if values.is_empty() {
            return Ok(InversionList {
                capacity,
                support: 0,
                intervals: Vec::new(),
            });
        }

        let mut sorted: Vec<u32> = values.to_vec();
        sorted.sort_unstable();
        sorted.dedup();

        if *sorted.last().unwrap() >= capacity {
            return Err(InversionListError::ValueOutOfRange(
                *sorted.last().unwrap(),
                capacity,
            ));
        }

        let mut intervals: Vec<(u32, u32)> = Vec::new();
        let mut start = sorted[0];
        let mut end = sorted[0] + 1;
        for &v in sorted.iter().skip(1) {
            if v == end {
                end = v + 1;
            } else {
                intervals.push((start, end));
                start = v;
                end = v + 1;
            }
        }
        intervals.push((start, end));

        let support = support_of(&intervals);

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
        self.intervals
            .iter()
            .any(|&(s, e)| value >= s && value < e)
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
        let support = self.capacity - self.support;
        InversionList {
            capacity: self.capacity,
            support,
            intervals,
        }
    }

    pub fn to_str(&self) -> String {
        let mut s = String::from("[");
        let mut first = true;
        for value in InversionListIterator::new(self) {
            if first {
                first = false;
            } else {
                s.push_str(", ");
            }
            s.push_str(&value.to_string());
        }
        s.push(']');
        s
    }

    pub fn equal(&self, other: &Self) -> bool {
        self.support == other.support && self.intervals == other.intervals
    }

    pub fn is_strict_subset_of(&self, other: &Self) -> bool {
        self.is_subset_of(other) && !self.equal(other)
    }

    pub fn is_subset_of(&self, other: &Self) -> bool {
        let inter = intersection_intervals(&self.intervals, &other.intervals);
        support_of(&inter) == self.support
    }

    pub fn is_disjoint(&self, other: &Self) -> bool {
        intersection_intervals(&self.intervals, &other.intervals).is_empty()
    }

    pub fn union(&self, other: &Self) -> Self {
        let intervals = union_intervals(&self.intervals, &other.intervals);
        let support = support_of(&intervals);
        let capacity = self.capacity.max(other.capacity);
        InversionList {
            capacity,
            support,
            intervals,
        }
    }

    pub fn intersection(&self, other: &Self) -> Self {
        let intervals = intersection_intervals(&self.intervals, &other.intervals);
        let support = support_of(&intervals);
        let capacity = self.capacity.max(other.capacity);
        InversionList {
            capacity,
            support,
            intervals,
        }
    }

    pub fn difference(&self, other: &Self) -> Self {
        let intervals = difference_intervals(&self.intervals, &other.intervals);
        let support = support_of(&intervals);
        let capacity = self.capacity.max(other.capacity);
        InversionList {
            capacity,
            support,
            intervals,
        }
    }

    pub fn symmetric_difference(&self, other: &Self) -> Self {
        let u = union_intervals(&self.intervals, &other.intervals);
        let i = intersection_intervals(&self.intervals, &other.intervals);
        let intervals = difference_intervals(&u, &i);
        let support = support_of(&intervals);
        let capacity = self.capacity.max(other.capacity);
        InversionList {
            capacity,
            support,
            intervals,
        }
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
            let (start, end) = self.list.intervals[self.interval_index];
            if self.current_value < start {
                self.current_value = start;
            }
            if self.current_value >= end {
                self.interval_index += 1;
                if self.interval_index < self.list.intervals.len() {
                    self.current_value = self.list.intervals[self.interval_index].0;
                }
                continue;
            }
            let value = self.current_value;
            self.current_value += 1;
            return Some(value);
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
        if self.couple_index >= self.list.intervals.len() {
            return None;
        }
        let couple = self.list.intervals[self.couple_index];
        self.couple_index += 1;
        Some(couple)
    }
}
