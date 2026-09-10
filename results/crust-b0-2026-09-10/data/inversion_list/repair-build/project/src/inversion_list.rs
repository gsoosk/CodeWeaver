use std::collections::BTreeSet;
use std::fmt;

#[derive(Debug)]
pub enum InversionListError {
    ValueOutOfRange(u32, u32),
    Generic(String),
}

impl fmt::Display for InversionListError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            InversionListError::ValueOutOfRange(value, capacity) => write!(
                f,
                "value {} is out of range for capacity {}",
                value, capacity
            ),
            InversionListError::Generic(msg) => write!(f, "{}", msg),
        }
    }
}

impl std::error::Error for InversionListError {}

#[derive(Clone, Debug)]
pub struct InversionList {
    capacity: u32,
    support: u32,
    pub intervals: Vec<(u32, u32)>,
}

impl InversionList {
    pub fn new(capacity: u32, values: &[u32]) -> Result<Self, InversionListError> {
        let mut sorted: Vec<u32> = values.to_vec();
        sorted.sort_unstable();
        sorted.dedup();

        if let Some(&max) = sorted.last() {
            if max >= capacity {
                return Err(InversionListError::ValueOutOfRange(max, capacity));
            }
        }

        let support = sorted.len() as u32;

        let mut intervals = Vec::new();
        let mut idx = 0usize;
        while idx < sorted.len() {
            let start = sorted[idx];
            let mut end = start + 1;
            idx += 1;
            while idx < sorted.len() && sorted[idx] == end {
                end += 1;
                idx += 1;
            }
            intervals.push((start, end));
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
        self.intervals
            .iter()
            .any(|&(s, e)| value >= s && value < e)
    }

    pub fn clone_list(&self) -> Self {
        self.clone()
    }

    pub fn complement(&self) -> Self {
        let mut intervals = Vec::new();
        let mut current = 0u32;

        for &(s, e) in &self.intervals {
            if current < s {
                intervals.push((current, s));
            }
            current = e;
        }

        if current < self.capacity {
            intervals.push((current, self.capacity));
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
        for &(start, end) in &self.intervals {
            for v in start..end {
                if !first {
                    s.push_str(", ");
                } else {
                    first = false;
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
        self.is_subset_of(other) && self.support < other.support
    }

    pub fn is_subset_of(&self, other: &Self) -> bool {
        self.to_values().iter().all(|&v| other.contains(v))
    }

    pub fn is_disjoint(&self, other: &Self) -> bool {
        self.to_values().iter().all(|&v| !other.contains(v))
    }

    fn to_values(&self) -> Vec<u32> {
        let mut values = Vec::new();
        for &(s, e) in &self.intervals {
            for v in s..e {
                values.push(v);
            }
        }
        values
    }

    pub fn union(&self, other: &Self) -> Self {
        let mut set: BTreeSet<u32> = BTreeSet::new();
        for v in self.to_values() {
            set.insert(v);
        }
        for v in other.to_values() {
            set.insert(v);
        }
        let capacity = self.capacity.max(other.capacity);
        let values: Vec<u32> = set.into_iter().collect();
        InversionList::new(capacity, &values).unwrap()
    }

    pub fn intersection(&self, other: &Self) -> Self {
        let values: Vec<u32> = self
            .to_values()
            .into_iter()
            .filter(|&v| other.contains(v))
            .collect();
        let capacity = self.capacity.max(other.capacity);
        InversionList::new(capacity, &values).unwrap()
    }

    pub fn difference(&self, other: &Self) -> Self {
        let values: Vec<u32> = self
            .to_values()
            .into_iter()
            .filter(|&v| !other.contains(v))
            .collect();
        let capacity = self.capacity.max(other.capacity);
        InversionList::new(capacity, &values).unwrap()
    }

    pub fn symmetric_difference(&self, other: &Self) -> Self {
        let mut values: Vec<u32> = self
            .to_values()
            .into_iter()
            .filter(|&v| !other.contains(v))
            .collect();
        values.extend(
            other
                .to_values()
                .into_iter()
                .filter(|&v| !self.contains(v)),
        );
        let capacity = self.capacity.max(other.capacity);
        InversionList::new(capacity, &values).unwrap()
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
        let current_value = list.intervals.get(0).map(|&(s, _)| s).unwrap_or(0);
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
        while self.interval_index < self.list.intervals.len() {
            let (s, e) = self.list.intervals[self.interval_index];
            if self.current_value < s {
                self.current_value = s;
            }
            if self.current_value < e {
                let val = self.current_value;
                self.current_value += 1;
                return Some(val);
            } else {
                self.interval_index += 1;
                if self.interval_index < self.list.intervals.len() {
                    self.current_value = self.list.intervals[self.interval_index].0;
                }
            }
        }
        None
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
