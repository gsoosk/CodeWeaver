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
impl InversionList {
    pub fn new(capacity: u32, values: &[u32]) -> Result<Self, InversionListError> {
        let mut buffer: Vec<u32> = values.to_vec();
        let count = buffer.len();
        let mut support: u32 = 0;
        let mut intervals: Vec<(u32, u32)> = Vec::new();
        if count > 0 {
            buffer.sort_unstable();
            let max = buffer[count - 1];
            if max >= capacity {
                return Err(InversionListError::ValueOutOfRange(max, capacity));
            }
            support = 1;
            let mut current_start = buffer[0];
            let mut current_end = buffer[0] + 1;
            for i in 1..count {
                if buffer[i] != buffer[i - 1] {
                    support += 1;
                }
                if buffer[i] == current_end {
                    current_end += 1;
                } else if buffer[i] > current_end {
                    intervals.push((current_start, current_end));
                    current_start = buffer[i];
                    current_end = buffer[i] + 1;
                }
            }
            intervals.push((current_start, current_end));
        }
        Ok(Self {
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
        // Mirrors `inversion_list_member`: intervals are sorted, non-overlapping
        // [start, end) ranges, so the first interval whose end exceeds `value`
        // decides membership (value < start means it fell in a gap).
        for &(start, end) in &self.intervals {
            if value < start {
                return false;
            }
            if value < end {
                return true;
            }
        }
        false
    }
    pub fn clone_list(&self) -> Self {
        // Mirrors `inversion_list_clone`: a plain field-wise copy with its own
        // freshly-allocated `intervals` Vec, so mutating one does not affect the other.
        self.clone()
    }
    pub fn complement(&self) -> Self {
        // Mirrors `inversion_list_complement`: walk the gaps between intervals
        // (and the leading/trailing gaps against 0/capacity), which naturally
        // handles all four boundary combinations (starts at 0 / ends at
        // capacity / neither / both) without needing the C's raw couples-array
        // splice logic.
        let capacity = self.capacity;
        let support = capacity - self.support;
        let mut intervals = Vec::new();
        let mut prev_end = 0u32;
        for &(start, end) in &self.intervals {
            if start > prev_end {
                intervals.push((prev_end, start));
            }
            prev_end = end;
        }
        if prev_end < capacity {
            intervals.push((prev_end, capacity));
        }
        Self {
            capacity,
            support,
            intervals,
        }
    }
    pub fn to_str(&self) -> String {
        // Mirrors `inversion_list_to_string`: expand every interval to its
        // individual member values and join with ", ", wrapped in "[" "]".
        let mut result = String::from("[");
        let mut first = true;
        for &(start, end) in &self.intervals {
            for value in start..end {
                if first {
                    first = false;
                } else {
                    result.push_str(", ");
                }
                result.push_str(&value.to_string());
            }
        }
        result.push(']');
        result
    }
    pub fn equal(&self, other: &Self) -> bool {
        // Mirrors `inversion_list_equal`: structural equality over (support, couples/intervals).
        self.support == other.support && self.intervals == other.intervals
    }
    pub fn is_strict_subset_of(&self, other: &Self) -> bool {
        // Mirrors `inversion_list_less` verbatim, quirks included: this is NOT a
        // true subset test. It returns false unless self's support is strictly
        // smaller than other's, and then merely probes whether `other` contains
        // *any* value below self's last interval's upper bound.
        if self.support >= other.support {
            return false;
        }
        // C reads `set1->couples[set1->size - 1]` (the last boundary value).
        // For an empty set that indexing is undefined in C; we treat "no last
        // boundary" as "no probe possible" and return false.
        let last = match self.intervals.last() {
            Some(&(_, end)) => end,
            None => return false,
        };
        let mut i: u32 = 0;
        let mut count: u32 = 0;
        while i < last && count < 1 {
            if other.contains(i) {
                count += 1;
            }
            i += 1;
        }
        count > 0
    }
    pub fn is_subset_of(&self, other: &Self) -> bool {
        // Mirrors `inversion_list_less_equal`: equal || less.
        self.equal(other) || self.is_strict_subset_of(other)
    }
    pub fn is_disjoint(&self, other: &Self) -> bool {
        // Mirrors `inversion_list_disjoint`, which is literally `not_equal` in
        // the C source (a bug/quirk) -- faithfully reproduced, not "fixed".
        !self.equal(other)
    }
    pub fn union(&self, other: &Self) -> Self {
        // Mirrors `_union`: scan every value between the smallest of the two
        // first boundaries and the largest of the two last boundaries,
        // keeping any value that is a member of either operand.
        let cap = self.capacity.max(other.capacity);
        if self.intervals.is_empty() && other.intervals.is_empty() {
            return Self {
                capacity: cap,
                support: 0,
                intervals: Vec::new(),
            };
        }
        let self_first = self.intervals.first().map(|&(s, _)| s);
        let other_first = other.intervals.first().map(|&(s, _)| s);
        let start = match (self_first, other_first) {
            (Some(a), Some(b)) => a.min(b),
            (Some(a), None) => a,
            (None, Some(b)) => b,
            (None, None) => unreachable!(),
        };
        let self_last = self.intervals.last().map(|&(_, e)| e);
        let other_last = other.intervals.last().map(|&(_, e)| e);
        let end = match (self_last, other_last) {
            (Some(a), Some(b)) => a.max(b),
            (Some(a), None) => a,
            (None, Some(b)) => b,
            (None, None) => unreachable!(),
        };
        let mut values = Vec::new();
        let mut i = start;
        loop {
            if self.contains(i) || other.contains(i) {
                values.push(i);
            }
            if i == end {
                break;
            }
            i += 1;
        }
        Self::new(cap, &values).unwrap()
    }
    pub fn intersection(&self, other: &Self) -> Self {
        // Mirrors `_intersection`: merge-walk both interval lists, checking
        // membership over the overlap of each pair of intervals.
        let cap = self.capacity.max(other.capacity);
        let mut values = Vec::new();
        let mut ii = 0usize;
        let mut jj = 0usize;
        while ii < self.intervals.len() && jj < other.intervals.len() {
            let (set1_min, set1_max) = self.intervals[ii];
            let (set2_min, set2_max) = other.intervals[jj];
            let min = set1_min.max(set2_min);
            let max = set1_max.min(set2_max);
            if min <= max {
                let mut k = min;
                loop {
                    if self.contains(k) && other.contains(k) {
                        values.push(k);
                    }
                    if k == max {
                        break;
                    }
                    k += 1;
                }
            }
            if set1_max < set2_max {
                ii += 1;
            } else if set1_max > set2_max {
                jj += 1;
            } else {
                ii += 1;
                jj += 1;
            }
        }
        Self::new(cap, &values).unwrap()
    }
    pub fn difference(&self, other: &Self) -> Self {
        // Mirrors `_difference` verbatim, including its leftover bug: the
        // "min" used in the overlap probe is always `self`'s very first
        // boundary (`set1->couples[0]`), not the current interval's start,
        // because the C source reads
        // `MAX(set1->couples[0], set1->couples[0])` instead of
        // `MAX(set1_min, set2_min)`. Also, once either interval list is
        // exhausted the merge-walk stops, so any trailing tail of `self`
        // beyond `other`'s last interval is silently dropped -- faithfully
        // reproduced, not fixed.
        let cap = self.capacity.max(other.capacity);
        let mut values = Vec::new();
        if self.intervals.is_empty() {
            return Self::new(cap, &values).unwrap();
        }
        let bugged_min = self.intervals[0].0;
        let mut ii = 0usize;
        let mut jj = 0usize;
        while ii < self.intervals.len() && jj < other.intervals.len() {
            let (set1_min, set1_max) = self.intervals[ii];
            let (_, set2_max) = other.intervals[jj];
            let max = set1_max.min(set2_max);
            if bugged_min <= max {
                let mut k = bugged_min;
                loop {
                    if self.contains(k) && !other.contains(k) {
                        values.push(k);
                    }
                    if k == max {
                        break;
                    }
                    k += 1;
                }
            }
            if set1_max < set2_max {
                let mut k = set1_min;
                while k < set2_max {
                    if self.contains(k) && !other.contains(k) {
                        values.push(k);
                    }
                    k += 1;
                }
                ii += 1;
            } else if set1_max > set2_max {
                jj += 1;
            } else {
                ii += 1;
                jj += 1;
            }
        }
        Self::new(cap, &values).unwrap()
    }
    pub fn symmetric_difference(&self, other: &Self) -> Self {
        // Mirrors `inversion_list_symmetric_difference`: (A ∪ B) - (A ∩ B).
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
        f.write_str(&self.to_str())
    }
}
pub struct InversionListIterator<'a> {
    list: &'a InversionList,
    interval_index: usize,
    current_value: u32,
}
impl<'a> InversionListIterator<'a> {
    pub fn new(list: &'a InversionList) -> Self {
        let current_value = list.intervals.get(0).map(|(lo, _)| *lo).unwrap_or(0);
        Self {
            list,
            interval_index: 0,
            current_value,
        }
    }
}
impl<'a> Iterator for InversionListIterator<'a> {
    type Item = u32;
    fn next(&mut self) -> Option<Self::Item> {
        if self.interval_index >= self.list.intervals.len() {
            return None;
        }
        let value = self.current_value;
        self.current_value += 1;
        let (_, end) = self.list.intervals[self.interval_index];
        if self.current_value >= end {
            self.interval_index += 1;
            if let Some(&(lo, _)) = self.list.intervals.get(self.interval_index) {
                self.current_value = lo;
            }
        }
        Some(value)
    }
}
pub struct InversionListCoupleIterator<'a> {
    list: &'a InversionList,
    couple_index: usize,
}
impl<'a> InversionListCoupleIterator<'a> {
    pub fn new(list: &'a InversionList) -> Self {
        Self {
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

// Unit-test seams: no mockable boundaries exist in this pure data-structure
// library (see analysis.md, "Unit-test strategy"), so these are plain
// behavioral tests mirroring the milestone matrix in pipeline/milestones.json.
// Each is `#[ignore]`d until the Translator fills in the corresponding
// implementation; the Translator must remove `#[ignore]` as each milestone
// lands. Stubs only -- no assertions/logic yet.
#[cfg(test)]
mod tests {
    use super::*;

    // M1: struct creation and destruction (mirrors `inversion_list_create`/`_destroy`).
    #[test]
    fn test_struct() {
        // Contiguous input 0,1,2 in a capacity-10 set: one interval [0,3), support 3.
        let set = InversionList::new(10, &[0, 1, 2]).unwrap();
        assert_eq!(set.capacity(), 10);
        assert_eq!(set.support(), 3);
        assert_eq!(set.intervals, vec![(0, 3)]);
    }

    #[test]
    fn test_create_destroy_2() {
        // Multiple disjoint values coalesce into separate intervals; dropping must not panic.
        let set = InversionList::new(20, &[1, 2, 5, 7, 8, 9]).unwrap();
        assert_eq!(set.capacity(), 20);
        assert_eq!(set.support(), 6);
        assert_eq!(set.intervals, vec![(1, 3), (5, 6), (7, 10)]);
        drop(set);

        // Empty values -> empty set, no panic on drop.
        let empty = InversionList::new(5, &[]).unwrap();
        assert_eq!(empty.support(), 0);
        assert!(empty.intervals.is_empty());
        drop(empty);
    }

    // M2: getters + creation edge cases (empty values, values >= capacity, duplicates/unsorted).
    #[test]
    fn test_getters() {
        let set = InversionList::new(100, &[3, 4, 5, 50]).unwrap();
        assert_eq!(set.capacity(), 100);
        assert_eq!(set.support(), 4);

        let empty = InversionList::new(1, &[]).unwrap();
        assert_eq!(empty.capacity(), 1);
        assert_eq!(empty.support(), 0);
    }

    #[test]
    fn test_create_destroy_3() {
        // Empty value set: capacity preserved, no intervals, support 0.
        let empty = InversionList::new(10, &[]).unwrap();
        assert_eq!(empty.capacity(), 10);
        assert_eq!(empty.support(), 0);
        assert!(empty.intervals.is_empty());

        // Value equal to capacity is out of range.
        let err = InversionList::new(5, &[5]).unwrap_err();
        match err {
            InversionListError::ValueOutOfRange(v, c) => {
                assert_eq!(v, 5);
                assert_eq!(c, 5);
            }
            _ => panic!("expected ValueOutOfRange"),
        }

        // Value exceeding capacity is out of range.
        let err = InversionList::new(5, &[7]).unwrap_err();
        match err {
            InversionListError::ValueOutOfRange(v, c) => {
                assert_eq!(v, 7);
                assert_eq!(c, 5);
            }
            _ => panic!("expected ValueOutOfRange"),
        }

        // Largest valid value (capacity - 1) is accepted.
        let set = InversionList::new(5, &[4]).unwrap();
        assert_eq!(set.support(), 1);
        assert_eq!(set.intervals, vec![(4, 5)]);
    }

    #[test]
    fn test_create_destroy_4() {
        // Duplicate values coalesce; support counts distinct values only.
        let set = InversionList::new(10, &[2, 2, 2, 3]).unwrap();
        assert_eq!(set.support(), 2);
        assert_eq!(set.intervals, vec![(2, 4)]);

        // Unsorted input is sorted internally before building intervals.
        let set = InversionList::new(10, &[9, 0, 5, 1]).unwrap();
        assert_eq!(set.support(), 4);
        assert_eq!(set.intervals, vec![(0, 2), (5, 6), (9, 10)]);

        // Unsorted + duplicate + out-of-range still detects the max correctly.
        let err = InversionList::new(5, &[1, 1, 9, 0]).unwrap_err();
        match err {
            InversionListError::ValueOutOfRange(v, c) => {
                assert_eq!(v, 9);
                assert_eq!(c, 5);
            }
            _ => panic!("expected ValueOutOfRange"),
        }
    }

    // M3: membership queries (mirrors `inversion_list_member`).
    #[test]
    fn test_member() {
        // Set with intervals [1,3), [5,6), [7,10) over capacity 20.
        let set = InversionList::new(20, &[1, 2, 5, 7, 8, 9]).unwrap();
        // Inside intervals.
        assert!(set.contains(1));
        assert!(set.contains(2));
        assert!(set.contains(5));
        assert!(set.contains(7));
        assert!(set.contains(8));
        assert!(set.contains(9));
        // Boundary: interval end is exclusive, so 3 (end of [1,3)) is not a member.
        assert!(!set.contains(3));
        assert!(!set.contains(6));
        assert!(!set.contains(10));
        // Outside any interval / gaps / start.
        assert!(!set.contains(0));
        assert!(!set.contains(4));
        assert!(!set.contains(19));

        // Empty set contains nothing.
        let empty = InversionList::new(10, &[]).unwrap();
        for v in 0..10 {
            assert!(!empty.contains(v));
        }

        // Single contiguous interval [0,3): boundary at start and end.
        let contiguous = InversionList::new(10, &[0, 1, 2]).unwrap();
        assert!(contiguous.contains(0));
        assert!(contiguous.contains(2));
        assert!(!contiguous.contains(3));

        // Largest valid value (capacity - 1) as boundary member.
        let edge = InversionList::new(5, &[4]).unwrap();
        assert!(edge.contains(4));
        assert!(!edge.contains(3));
    }

    // M4: cloning (mirrors `inversion_list_clone`).
    #[test]
    fn test_clone() {
        let original = InversionList::new(20, &[1, 2, 5, 7, 8, 9]).unwrap();
        let cloned = original.clone_list();
        assert!(cloned.equal(&original));
        assert_eq!(cloned.capacity(), original.capacity());
        assert_eq!(cloned.support(), original.support());
        assert_eq!(cloned.intervals, original.intervals);

        // Mutating the clone's intervals (by rebuilding it) must not affect the original.
        let mut mutated = cloned;
        mutated.intervals = vec![(0, 1)];
        assert_ne!(mutated.intervals, original.intervals);
        assert_eq!(original.intervals, vec![(1, 3), (5, 6), (7, 10)]);

        // Cloning the empty set works too.
        let empty = InversionList::new(10, &[]).unwrap();
        let empty_clone = empty.clone_list();
        assert!(empty_clone.equal(&empty));
        assert!(empty_clone.intervals.is_empty());
    }

    // M5: string conversion (mirrors `inversion_list_to_string`).
    #[test]
    fn test_to_string() {
        // Empty set formats as "[]".
        let empty = InversionList::new(10, &[]).unwrap();
        assert_eq!(empty.to_str(), "[]");
        assert_eq!(format!("{}", empty), "[]");

        // Single contiguous interval expands to each member value.
        let set = InversionList::new(10, &[0, 1, 2]).unwrap();
        assert_eq!(set.to_str(), "[0, 1, 2]");
        assert_eq!(format!("{}", set), "[0, 1, 2]");

        // Multiple disjoint intervals expand in ascending order.
        let multi = InversionList::new(20, &[1, 2, 5, 7, 8, 9]).unwrap();
        assert_eq!(multi.to_str(), "[1, 2, 5, 7, 8, 9]");
        assert_eq!(format!("{}", multi), "[1, 2, 5, 7, 8, 9]");

        // Single-element set.
        let single = InversionList::new(5, &[4]).unwrap();
        assert_eq!(single.to_str(), "[4]");
        assert_eq!(format!("{}", single), "[4]");
    }

    // M6: equality/ordering comparisons (mirrors `_equal`/`_not_equal`/`_less`/`_less_equal`/
    // `_greater`/`_greater_equal`/`_disjoint`, quirks included).
    #[test]
    fn test_equals() {
        // A: intervals [(1,3),(5,6),(7,10)], support 6.
        let a = InversionList::new(20, &[1, 2, 5, 7, 8, 9]).unwrap();
        // B: intervals [(1,3)], support 2 -- a true subset of A's values.
        let b = InversionList::new(20, &[1, 2]).unwrap();
        // C: intervals [(15,17)], support 2 -- disjoint from A's actual values.
        let c = InversionList::new(20, &[15, 16]).unwrap();
        let empty = InversionList::new(20, &[]).unwrap();

        // equal / PartialEq / not_equal.
        assert!(a.equal(&a));
        assert_eq!(a, a.clone_list());
        assert!(!a.equal(&b));
        assert_ne!(a, b);

        // is_strict_subset_of: false whenever support(self) >= support(other).
        assert!(!a.is_strict_subset_of(&b)); // support 6 >= 2
        assert!(!a.is_strict_subset_of(&a)); // equal supports

        // B has smaller support than A and its last boundary (3) probe finds
        // member 1 in A on the first try -> true (and here B genuinely is a
        // subset, so this case looks "correct").
        assert!(b.is_strict_subset_of(&a));

        // Faithful quirk: C has smaller support than A, and even though C's
        // actual values (15, 16) are NOT members of A, the buggy probe only
        // scans 0..last_boundary(=17) and finds A's member 1 well before
        // reaching C's real values, so it wrongly reports "less".
        assert!(c.is_strict_subset_of(&a));

        // Empty set: smaller support than A, but no last boundary to probe.
        assert!(!empty.is_strict_subset_of(&a));

        // is_subset_of = equal || is_strict_subset_of.
        assert!(a.is_subset_of(&a));
        assert!(b.is_subset_of(&a));
        assert!(!a.is_subset_of(&b));

        // is_disjoint is literally `!equal`, not true set-disjointness: B
        // shares members with A yet reports "disjoint" because it isn't equal,
        // while A is never "disjoint" from itself.
        assert!(a.is_disjoint(&b));
        assert!(a.is_disjoint(&c));
        assert!(!a.is_disjoint(&a));
    }

    // M7: value iterator (mirrors `InversionListIterator` family).
    #[test]
    fn test_iterator() {
        // Multi-interval set: iterator visits every member ascending exactly once.
        let set = InversionList::new(20, &[1, 2, 5, 7, 8, 9]).unwrap();
        let values: Vec<u32> = InversionListIterator::new(&set).collect();
        assert_eq!(values, vec![1, 2, 5, 7, 8, 9]);

        // Single contiguous interval.
        let contiguous = InversionList::new(10, &[0, 1, 2]).unwrap();
        let values: Vec<u32> = InversionListIterator::new(&contiguous).collect();
        assert_eq!(values, vec![0, 1, 2]);

        // Empty set: iterator yields no items.
        let empty = InversionList::new(10, &[]).unwrap();
        let values: Vec<u32> = InversionListIterator::new(&empty).collect();
        assert!(values.is_empty());

        // Explicit next()/exhaustion check.
        let mut it = InversionListIterator::new(&empty);
        assert_eq!(it.next(), None);
    }

    // M8: couple iterator (mirrors `InversionListCoupleIterator` family).
    #[test]
    fn test_couple_iterator() {
        let set = InversionList::new(20, &[1, 2, 3, 10, 11, 15]).unwrap();
        let couples: Vec<(u32, u32)> = InversionListCoupleIterator::new(&set).collect();
        assert_eq!(couples, vec![(1, 4), (10, 12), (15, 16)]);

        // Empty set: iterator yields no items.
        let empty = InversionList::new(10, &[]).unwrap();
        let couples: Vec<(u32, u32)> = InversionListCoupleIterator::new(&empty).collect();
        assert!(couples.is_empty());

        // Explicit next()/exhaustion check.
        let mut it = InversionListCoupleIterator::new(&empty);
        assert_eq!(it.next(), None);
    }

    // M9: set algebra (mirrors `_union`/`_intersection`/`_difference`/`_symmetric_difference`).
    #[test]
    fn test_complement() {
        // Neither starts at 0 nor ends at capacity: gaps added on both sides.
        let set = InversionList::new(20, &[5, 6, 7, 12, 13]).unwrap();
        let comp = set.complement();
        assert_eq!(comp.capacity(), 20);
        assert_eq!(comp.support(), 20 - 5);
        assert_eq!(comp.intervals, vec![(0, 5), (8, 12), (14, 20)]);

        // Starts at 0, does not end at capacity: only trailing gap added.
        let starts_at_zero = InversionList::new(10, &[0, 1, 2]).unwrap();
        let comp2 = starts_at_zero.complement();
        assert_eq!(comp2.support(), 10 - 3);
        assert_eq!(comp2.intervals, vec![(3, 10)]);

        // Ends at capacity, does not start at 0: only leading gap added.
        let ends_at_capacity = InversionList::new(10, &[7, 8, 9]).unwrap();
        let comp3 = ends_at_capacity.complement();
        assert_eq!(comp3.support(), 10 - 3);
        assert_eq!(comp3.intervals, vec![(0, 7)]);

        // Both starts at 0 and ends at capacity: entire range covered, complement is empty.
        let full = InversionList::new(5, &[0, 1, 2, 3, 4]).unwrap();
        let comp4 = full.complement();
        assert_eq!(comp4.support(), 0);
        assert!(comp4.intervals.is_empty());

        // Empty set: complement is the entire range.
        let empty = InversionList::new(10, &[]).unwrap();
        let comp5 = empty.complement();
        assert_eq!(comp5.support(), 10);
        assert_eq!(comp5.intervals, vec![(0, 10)]);
    }

    #[test]
    fn test_union() {
        // Overlapping intervals merge into one.
        let a = InversionList::new(20, &[1, 2, 3, 4]).unwrap();
        let b = InversionList::new(20, &[3, 4, 5, 6]).unwrap();
        let u = a.union(&b);
        assert_eq!(u.intervals, vec![(1, 7)]);
        assert_eq!(u.support(), 6);
        assert_eq!(u.capacity(), 20);

        // Disjoint intervals stay separate.
        let c = InversionList::new(20, &[1, 2]).unwrap();
        let d = InversionList::new(20, &[10, 11]).unwrap();
        let u2 = c.union(&d);
        assert_eq!(u2.intervals, vec![(1, 3), (10, 12)]);

        // Touching intervals (end of one == start of the other) merge.
        let e = InversionList::new(20, &[1, 2]).unwrap();
        let f = InversionList::new(20, &[3, 4]).unwrap();
        let u3 = e.union(&f);
        assert_eq!(u3.intervals, vec![(1, 5)]);

        // Union with an empty set returns the other set's values.
        let empty = InversionList::new(20, &[]).unwrap();
        let u4 = c.union(&empty);
        assert_eq!(u4.intervals, c.intervals);
        let u5 = empty.union(&c);
        assert_eq!(u5.intervals, c.intervals);

        // Union of two empty sets is empty.
        let empty2 = InversionList::new(20, &[]).unwrap();
        let u6 = empty.union(&empty2);
        assert!(u6.intervals.is_empty());

        // Capacity of the union is the max of both operands' capacities.
        let g = InversionList::new(10, &[1]).unwrap();
        let h = InversionList::new(30, &[2]).unwrap();
        assert_eq!(g.union(&h).capacity(), 30);
    }

    #[test]
    fn test_intersection() {
        // Overlapping intervals keep only the shared values.
        let a = InversionList::new(20, &[1, 2, 3, 4]).unwrap();
        let b = InversionList::new(20, &[3, 4, 5, 6]).unwrap();
        let i = a.intersection(&b);
        assert_eq!(i.intervals, vec![(3, 5)]);
        assert_eq!(i.support(), 2);

        // Disjoint intervals intersect to nothing.
        let c = InversionList::new(20, &[1, 2]).unwrap();
        let d = InversionList::new(20, &[10, 11]).unwrap();
        let i2 = c.intersection(&d);
        assert!(i2.intervals.is_empty());

        // Touching intervals (no shared values) intersect to nothing.
        let e = InversionList::new(20, &[1, 2]).unwrap();
        let f = InversionList::new(20, &[3, 4]).unwrap();
        let i3 = e.intersection(&f);
        assert!(i3.intervals.is_empty());

        // Intersection with an empty set is empty.
        let empty = InversionList::new(20, &[]).unwrap();
        let i4 = c.intersection(&empty);
        assert!(i4.intervals.is_empty());

        // Identical sets intersect to themselves.
        let g = InversionList::new(20, &[5, 6, 7]).unwrap();
        let i5 = g.intersection(&g.clone_list());
        assert_eq!(i5.intervals, g.intervals);
    }

    #[test]
    fn test_difference() {
        // Overlapping intervals: keep only self's values not in other.
        let a = InversionList::new(20, &[1, 2, 3, 4]).unwrap();
        let b = InversionList::new(20, &[3, 4, 5, 6]).unwrap();
        let diff = a.difference(&b);
        assert_eq!(diff.intervals, vec![(1, 3)]);

        // Disjoint operands: difference against an empty-intersection interval is
        // still governed by the C source's leftover bug, whereby the merge-walk
        // terminates once either interval list is exhausted, so a self-tail
        // beyond other's coverage is silently dropped.
        let c = InversionList::new(20, &[1, 2]).unwrap();
        let d = InversionList::new(20, &[10, 11]).unwrap();
        let diff2 = c.difference(&d);
        assert_eq!(diff2.intervals, vec![(1, 3)]);

        // Touching intervals: no overlap, so self's values are all kept.
        let e = InversionList::new(20, &[1, 2]).unwrap();
        let f = InversionList::new(20, &[3, 4]).unwrap();
        let diff3 = e.difference(&f);
        assert_eq!(diff3.intervals, vec![(1, 3)]);

        // Difference against an empty other returns empty, per the C bug: the
        // merge-walk never enters its loop body when `other` has zero intervals.
        let empty = InversionList::new(20, &[]).unwrap();
        let diff4 = c.difference(&empty);
        assert!(diff4.intervals.is_empty());

        // Difference of an empty self is empty.
        let diff5 = empty.difference(&c);
        assert!(diff5.intervals.is_empty());

        // Identical sets: difference is empty.
        let g = InversionList::new(20, &[5, 6, 7]).unwrap();
        let diff6 = g.difference(&g.clone_list());
        assert!(diff6.intervals.is_empty());
    }

    #[test]
    fn test_symmetric_difference() {
        // (A ∪ B) - (A ∩ B), composed from the (already-bug-faithful) union/
        // intersection/difference primitives above. Because `difference`'s
        // merge-walk stops as soon as either operand's interval list is
        // exhausted, the mathematically "ideal" symmetric-difference values
        // beyond that point get silently dropped here too -- faithfully
        // inherited from the C source's composition, not an independent bug.
        let a = InversionList::new(20, &[1, 2, 3, 4]).unwrap();
        let b = InversionList::new(20, &[3, 4, 5, 6]).unwrap();
        let sym = a.symmetric_difference(&b);
        assert_eq!(sym.intervals, vec![(1, 3), (5, 6)]);

        // Disjoint sets: intersection is empty, and difference against a
        // literal empty `other` returns empty per the inherited bug (the
        // merge-walk never enters its loop body when `other` has zero
        // intervals), so the symmetric difference here is empty too.
        let c = InversionList::new(20, &[1, 2]).unwrap();
        let d = InversionList::new(20, &[10, 11]).unwrap();
        let sym2 = c.symmetric_difference(&d);
        assert!(sym2.intervals.is_empty());
    }
}