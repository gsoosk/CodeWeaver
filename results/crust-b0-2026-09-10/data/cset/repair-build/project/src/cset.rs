// Import necessary modules
use std::mem;
use std::ptr;
// Type aliases
pub type XXH64HashT = u64;
pub type XXHU8 = u8;
pub type XXHU64 = XXH64HashT;
pub type XXHU32 = u32;
pub type XXH32HashT = u32;
// Constants
pub const XXH_PRIME64_1: u64 = 0x9E3779B185EBCA87;
pub const XXH_PRIME64_2: u64 = 0xC2B2AE3D27D4EB4F;
pub const XXH_PRIME64_3: u64 = 0x165667B19E3779F9;
pub const XXH_PRIME64_4: u64 = 0x85EBCA77C2B2AE63;
pub const XXH_PRIME64_5: u64 = 0x27D4EB2F165667C5;
pub const CSET_FORCE_INITIALIZE: bool = true;
pub const CSET_INITIAL_CAP: usize = 2;
pub const CSET_DEFAULT_SEED: u64 = 2718182;
pub const CSET_MAX_LOAD_FACTOR: f64 = 0.7;
pub const CSET_MIN_LOAD_FACTOR: f64 = 0.2;

// ---------------------------------------------------------------------------
// xxhash64 implementation
// ---------------------------------------------------------------------------

pub fn xxh_get64bits(mem_ptr: &mut XXHU8) -> XXHU64 {
    xxh_read_le64_align(mem_ptr)
}

pub fn xxh_read_le64(mem_ptr: &mut XXHU8) -> XXHU64 {
    let byte_ptr: *mut u8 = mem_ptr;
    unsafe {
        let mut result: u64 = 0;
        for i in 0..8 {
            result |= (*byte_ptr.add(i) as u64) << (8 * i);
        }
        result
    }
}

pub fn xxh_is_little_endian() -> bool {
    cfg!(target_endian = "little")
}

pub fn xxh_read_le64_align(mem_ptr: &mut XXHU8) -> XXHU64 {
    xxh_read_le64(mem_ptr)
}

pub fn xxh_swap32(x: &mut XXHU32) -> XXHU32 {
    let x = *x;
    ((x << 24) & 0xff000000)
        | ((x << 8) & 0x00ff0000)
        | ((x >> 8) & 0x0000ff00)
        | ((x >> 24) & 0x000000ff)
}

pub fn xxh_read32(mem_ptr: &mut XXHU32) -> XXHU32 {
    *mem_ptr
}

pub fn xxh64_round(acc: XXHU64, input: XXHU64) -> XXHU64 {
    let mut acc = acc;
    acc = acc.wrapping_add(input.wrapping_mul(XXH_PRIME64_2));
    acc = acc.rotate_left(31);
    acc = acc.wrapping_mul(XXH_PRIME64_1);
    acc
}

pub fn xxh64_merge_round(acc: XXHU64, val: XXHU64) -> XXHU64 {
    let mut acc = acc;
    let val = xxh64_round(0, val);
    acc ^= val;
    acc = acc.wrapping_mul(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_4);
    acc
}

pub fn xxh_get_32bits(ptr: &mut XXHU32) -> XXHU32 {
    xxh_read_le32_align(ptr)
}

pub fn xxh_read_le32_align(ptr: &mut XXHU32) -> XXHU32 {
    let byte_ptr: *mut u32 = ptr;
    let byte_ptr = byte_ptr as *mut u8;
    unsafe {
        (*byte_ptr as u32)
            | ((*byte_ptr.add(1) as u32) << 8)
            | ((*byte_ptr.add(2) as u32) << 16)
            | ((*byte_ptr.add(3) as u32) << 24)
    }
}

pub fn xxh64_avalanche(h64: XXHU64) -> XXHU64 {
    let mut h64 = h64;
    h64 ^= h64 >> 33;
    h64 = h64.wrapping_mul(XXH_PRIME64_2);
    h64 ^= h64 >> 29;
    h64 = h64.wrapping_mul(XXH_PRIME64_3);
    h64 ^= h64 >> 32;
    h64
}

pub fn xxh64_finalize(h64: XXHU64, ptr: &mut XXHU8, len: usize) -> XXHU64 {
    let mut h64 = h64;
    let mut len = len & 31;
    let mut p: *mut u8 = ptr;
    unsafe {
        while len >= 8 {
            let k1 = xxh64_round(0, xxh_read_le64(&mut *p));
            p = p.add(8);
            h64 ^= k1;
            h64 = h64
                .rotate_left(27)
                .wrapping_mul(XXH_PRIME64_1)
                .wrapping_add(XXH_PRIME64_4);
            len -= 8;
        }
        if len >= 4 {
            let v = (*p as u32)
                | ((*p.add(1) as u32) << 8)
                | ((*p.add(2) as u32) << 16)
                | ((*p.add(3) as u32) << 24);
            h64 ^= (v as u64).wrapping_mul(XXH_PRIME64_1);
            p = p.add(4);
            h64 = h64
                .rotate_left(23)
                .wrapping_mul(XXH_PRIME64_2)
                .wrapping_add(XXH_PRIME64_3);
            len -= 4;
        }
        while len > 0 {
            h64 ^= (*p as u64).wrapping_mul(XXH_PRIME64_5);
            p = p.add(1);
            h64 = h64.rotate_left(11).wrapping_mul(XXH_PRIME64_1);
            len -= 1;
        }
    }
    xxh64_avalanche(h64)
}

pub fn xxh64_endian_align(input: &mut XXHU8, len: usize, seed: XXHU64) -> XXHU64 {
    let mut p: *mut u8 = input;
    let mut h64: u64;
    unsafe {
        if len >= 32 {
            let b_end = p.add(len);
            let limit = b_end.sub(32);
            let mut v1 = seed.wrapping_add(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_2);
            let mut v2 = seed.wrapping_add(XXH_PRIME64_2);
            let mut v3 = seed.wrapping_add(0);
            let mut v4 = seed.wrapping_sub(XXH_PRIME64_1);
            loop {
                v1 = xxh64_round(v1, xxh_read_le64(&mut *p));
                p = p.add(8);
                v2 = xxh64_round(v2, xxh_read_le64(&mut *p));
                p = p.add(8);
                v3 = xxh64_round(v3, xxh_read_le64(&mut *p));
                p = p.add(8);
                v4 = xxh64_round(v4, xxh_read_le64(&mut *p));
                p = p.add(8);
                if p > limit {
                    break;
                }
            }
            h64 = v1
                .rotate_left(1)
                .wrapping_add(v2.rotate_left(7))
                .wrapping_add(v3.rotate_left(12))
                .wrapping_add(v4.rotate_left(18));
            h64 = xxh64_merge_round(h64, v1);
            h64 = xxh64_merge_round(h64, v2);
            h64 = xxh64_merge_round(h64, v3);
            h64 = xxh64_merge_round(h64, v4);
        } else {
            h64 = seed.wrapping_add(XXH_PRIME64_5);
        }
        h64 = h64.wrapping_add(len as u64);
        xxh64_finalize(h64, &mut *p, len)
    }
}

pub fn xxh64_endian_align_h(input: &mut XXHU8, len: usize, seed: XXHU64) -> XXHU64 {
    let mut p: *mut u8 = input;
    let mut h64: u64;
    unsafe {
        if len >= 32 {
            let b_end = p.add(len);
            let limit = b_end.sub(32);
            let mut v1 = seed.wrapping_add(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_2);
            let mut v2 = seed.wrapping_sub(XXH_PRIME64_2);
            let mut v3 = seed.wrapping_add(XXH_PRIME64_3);
            let mut v4 = seed.wrapping_sub(XXH_PRIME64_1);
            loop {
                v1 = xxh64_round(v1, xxh_read_le64(&mut *p));
                p = p.add(8);
                v2 = xxh64_round(v2, xxh_read_le64(&mut *p));
                p = p.add(8);
                v3 = xxh64_round(v3, xxh_read_le64(&mut *p));
                p = p.add(8);
                v4 = xxh64_round(v4, xxh_read_le64(&mut *p));
                p = p.add(8);
                if p > limit {
                    break;
                }
            }
            h64 = v1
                .rotate_left(1)
                .wrapping_add(v2.rotate_left(7))
                .wrapping_add(v3.rotate_left(12))
                .wrapping_add(v4.rotate_left(18));
            h64 = xxh64_merge_round(h64, v1);
            h64 = xxh64_merge_round(h64, v2);
            h64 = xxh64_merge_round(h64, v3);
            h64 = xxh64_merge_round(h64, v4);
        } else {
            h64 = seed.wrapping_add(XXH_PRIME64_1);
        }
        h64 = h64.wrapping_add(len as u64);
        xxh64_finalize(h64, &mut *p, len)
    }
}

pub fn xxh64(input: *const u8, len: usize, seed: XXH64HashT) -> XXH64HashT {
    if input.is_null() {
        return xxh64_avalanche(seed.wrapping_add(XXH_PRIME64_5));
    }
    unsafe { xxh64_endian_align(&mut *(input as *mut u8), len, seed) }
}

pub fn xxh64_h(input: *const u8, len: usize, seed: XXH64HashT) -> XXH64HashT {
    if input.is_null() {
        return xxh64_avalanche(seed.wrapping_add(XXH_PRIME64_1));
    }
    unsafe { xxh64_endian_align_h(&mut *(input as *mut u8), len, seed) }
}

pub fn cset_hash1_callback(memptr: &mut XXHU8, size: usize) -> XXHU64 {
    let p: *mut u8 = memptr;
    xxh64(p as *const u8, size, CSET_DEFAULT_SEED)
}

pub fn cset_hash2_callback(memptr: &mut XXHU8, size: usize) -> XXHU64 {
    let p: *mut u8 = memptr;
    xxh64_h(p as *const u8, size, CSET_DEFAULT_SEED) | 1
}

// ---------------------------------------------------------------------------
// Cset: an open-addressed, double-hashed hash set
// ---------------------------------------------------------------------------

pub struct CsetValue<T> {
    pi: i32,
    elem: T,
}

pub struct Cset<T> {
    buckets: Vec<CsetValue<T>>,
    max_load_factor: f64,
    min_load_factor: f64,
    seed: u64,
    v: CsetValue<T>,
    bucket_size: usize,
    compare: Option<fn(&T, &T) -> bool>,
    temp_buckets: Vec<CsetValue<T>>,
}

impl<T: Clone + PartialEq + Default> Cset<T> {
    pub fn new() -> Cset<T> {
        let mut buckets = Vec::with_capacity(CSET_INITIAL_CAP);
        for _ in 0..CSET_INITIAL_CAP {
            buckets.push(CsetValue {
                pi: 0,
                elem: T::default(),
            });
        }
        Cset {
            buckets,
            max_load_factor: CSET_MAX_LOAD_FACTOR,
            min_load_factor: CSET_MIN_LOAD_FACTOR,
            seed: CSET_DEFAULT_SEED,
            v: CsetValue {
                pi: 0,
                elem: T::default(),
            },
            bucket_size: 0,
            compare: None,
            temp_buckets: Vec::new(),
        }
    }

    pub fn empty(&self) -> bool {
        self.bucket_size == 0
    }

    pub fn tombstone(&self) -> bool {
        false
    }

    pub fn index(&self, index: usize) -> T {
        self.buckets[index].elem.clone()
    }

    pub fn get_size(&self) -> usize {
        self.bucket_size
    }

    pub fn set_size(&mut self, new_size: usize) {
        self.bucket_size = new_size;
    }

    pub fn get_seed(&self) -> u64 {
        self.seed
    }

    pub fn set_seed(&mut self, seed: u64) {
        self.seed = seed;
    }

    pub fn get_max_load_factor(&self) -> f64 {
        self.max_load_factor
    }

    pub fn set_max_load_factor(&mut self, new_factor: f64) {
        self.max_load_factor = new_factor;
    }

    pub fn get_min_load_factor(&self) -> f64 {
        self.min_load_factor
    }

    pub fn set_min_load_factor(&mut self, new_factor: f64) {
        self.min_load_factor = new_factor;
    }

    pub fn get_buckets(&self) -> &Vec<CsetValue<T>> {
        &self.buckets
    }

    pub fn get_buckets_ref(&self) -> &mut Vec<CsetValue<T>> {
        unsafe { &mut *(&self.buckets as *const Vec<CsetValue<T>> as *mut Vec<CsetValue<T>>) }
    }

    pub fn get_temp_buckets_ref(&self) -> &mut Vec<CsetValue<T>> {
        unsafe {
            &mut *(&self.temp_buckets as *const Vec<CsetValue<T>> as *mut Vec<CsetValue<T>>)
        }
    }

    pub fn size(&self) -> i32 {
        self.bucket_size as i32
    }

    pub fn capacity(&self) -> i32 {
        self.buckets.len() as i32
    }

    fn hash1(&self, value: &T) -> u64 {
        let size = mem::size_of::<T>();
        let ptr = value as *const T as *const u8;
        xxh64(ptr, size, self.seed)
    }

    fn hash2(&self, value: &T) -> u64 {
        let size = mem::size_of::<T>();
        let ptr = value as *const T as *const u8;
        xxh64_h(ptr, size, self.seed) | 1
    }

    fn double_hash_index(h1: u64, h2: u64, i: usize, cap: usize) -> usize {
        ((h1.wrapping_add((i as u64).wrapping_mul(h2))) % (cap as u64)) as usize
    }

    fn matches(&self, index: usize, value: &T) -> bool {
        match &self.compare {
            Some(cmp) => cmp(&self.buckets[index].elem, value),
            None => self.buckets[index].elem == *value,
        }
    }

    fn add_internal(&mut self, value: T) -> i32 {
        let h1 = self.hash1(&value);
        let cap = self.buckets.len();
        let mut iteration: usize = 1;
        let mut index: usize = 0;
        let mut found = false;
        loop {
            let h2 = self.hash2(&value);
            index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            if self.buckets[index].pi == 0 || self.buckets[index].pi == -1 {
                break;
            }
            if self.matches(index, &value) {
                found = true;
                break;
            }
        }
        if !found {
            self.buckets[index].elem = value;
            self.buckets[index].pi = iteration as i32;
            self.bucket_size += 1;
            1
        } else {
            0
        }
    }

    fn resize(&mut self, new_cap: usize) {
        let current_cap = self.buckets.len();
        let mut new_buckets = Vec::with_capacity(new_cap);
        for _ in 0..new_cap {
            new_buckets.push(CsetValue {
                pi: 0,
                elem: T::default(),
            });
        }
        let old_buckets = mem::replace(&mut self.buckets, new_buckets);
        self.bucket_size = 0;
        for i in 0..current_cap {
            let pi = old_buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let val = old_buckets[i].elem.clone();
            self.add_internal(val);
        }
    }

    pub fn add(&mut self, value: T) -> i32 {
        let load = self.bucket_size as f64 / self.buckets.len() as f64;
        if load >= self.max_load_factor {
            self.resize(self.buckets.len() * 2);
        }
        self.add_internal(value)
    }

    pub fn remove(&mut self, value: T) -> i32 {
        let h1 = self.hash1(&value);
        let cap = self.buckets.len();
        let mut iteration: usize = 1;
        let mut index: usize = 0;
        let mut found = false;
        loop {
            if iteration - 1 >= cap {
                break;
            }
            let h2 = self.hash2(&value);
            index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            if self.buckets[index].pi == -1 {
                continue;
            }
            if self.buckets[index].pi == 0 {
                break;
            }
            if self.matches(index, &value) {
                found = true;
                break;
            }
        }
        if found {
            self.buckets[index].pi = -1;
            self.bucket_size -= 1;
            1
        } else {
            0
        }
    }

    fn contains_impl(&self, value: &T) -> bool {
        let h1 = self.hash1(value);
        let cap = self.buckets.len();
        let mut iteration: usize = 1;
        let mut found = false;
        loop {
            if iteration - 1 >= cap {
                break;
            }
            let h2 = self.hash2(value);
            let index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            if self.buckets[index].pi == -1 {
                continue;
            }
            if self.buckets[index].pi == 0 {
                break;
            }
            if self.matches(index, value) {
                found = true;
                break;
            }
        }
        found
    }

    pub fn contains(&mut self, value: &T) -> bool {
        self.contains_impl(value)
    }

    pub fn iter(&mut self) -> Vec<T> {
        let mut result = Vec::new();
        for b in &self.buckets {
            if b.pi == 0 || b.pi == -1 {
                continue;
            }
            result.push(b.elem.clone());
        }
        result
    }

    pub fn set_comparator(&mut self, compare: fn(&T, &T) -> bool) {
        self.compare = Some(compare);
    }

    pub fn clear(&mut self) {
        let mut buckets = Vec::with_capacity(CSET_INITIAL_CAP);
        for _ in 0..CSET_INITIAL_CAP {
            buckets.push(CsetValue {
                pi: 0,
                elem: T::default(),
            });
        }
        self.buckets = buckets;
        self.bucket_size = 0;
    }

    pub fn intersect(&mut self, first: &Self, second: &Self) {
        for b in &first.buckets {
            if b.pi == 0 || b.pi == -1 {
                continue;
            }
            if second.contains_impl(&b.elem) {
                self.add(b.elem.clone());
            }
        }
    }

    pub fn union(&mut self, first: &Self, second: &Self) {
        for b in &first.buckets {
            if b.pi == 0 || b.pi == -1 {
                continue;
            }
            self.add(b.elem.clone());
        }
        for b in &second.buckets {
            if b.pi == 0 || b.pi == -1 {
                continue;
            }
            self.add(b.elem.clone());
        }
    }

    pub fn is_disjoint(&mut self, other: &Self) -> bool {
        for b in &self.buckets {
            if b.pi == 0 || b.pi == -1 {
                continue;
            }
            if other.contains_impl(&b.elem) {
                return false;
            }
        }
        true
    }

    pub fn difference(&mut self, first: &Self, second: &Self) {
        for b in &first.buckets {
            if b.pi == 0 || b.pi == -1 {
                continue;
            }
            if !second.contains_impl(&b.elem) {
                self.add(b.elem.clone());
            }
        }
    }
}
