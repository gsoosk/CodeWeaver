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

// ---------------------------------------------------------------------
// Low level byte-slice based implementation of the xxHash64 algorithm.
// These are used internally by `Cset` to hash values in a safe,
// idiomatic way (slice indexing instead of raw pointer arithmetic).
// ---------------------------------------------------------------------

fn read_le64_slice(b: &[u8]) -> u64 {
    (b[0] as u64)
        | ((b[1] as u64) << 8)
        | ((b[2] as u64) << 16)
        | ((b[3] as u64) << 24)
        | ((b[4] as u64) << 32)
        | ((b[5] as u64) << 40)
        | ((b[6] as u64) << 48)
        | ((b[7] as u64) << 56)
}

fn read_le32_slice(b: &[u8]) -> u32 {
    (b[0] as u32) | ((b[1] as u32) << 8) | ((b[2] as u32) << 16) | ((b[3] as u32) << 24)
}

fn xxh64_finalize_bytes(mut h64: u64, bytes: &[u8]) -> u64 {
    let mut len = bytes.len() & 31;
    let mut offset = 0usize;
    while len >= 8 {
        let k1 = xxh64_round(0, read_le64_slice(&bytes[offset..offset + 8]));
        offset += 8;
        h64 ^= k1;
        h64 = h64
            .rotate_left(27)
            .wrapping_mul(XXH_PRIME64_1)
            .wrapping_add(XXH_PRIME64_4);
        len -= 8;
    }
    if len >= 4 {
        let v32 = read_le32_slice(&bytes[offset..offset + 4]);
        h64 ^= (v32 as u64).wrapping_mul(XXH_PRIME64_1);
        offset += 4;
        h64 = h64
            .rotate_left(23)
            .wrapping_mul(XXH_PRIME64_2)
            .wrapping_add(XXH_PRIME64_3);
        len -= 4;
    }
    while len > 0 {
        h64 ^= (bytes[offset] as u64).wrapping_mul(XXH_PRIME64_5);
        offset += 1;
        h64 = h64.rotate_left(11).wrapping_mul(XXH_PRIME64_1);
        len -= 1;
    }
    xxh64_avalanche(h64)
}

fn xxh64_core(seed: u64, bytes: &[u8]) -> u64 {
    let len = bytes.len();
    let mut h64: u64;
    let mut offset = 0usize;
    if len >= 32 {
        let limit = len - 32;
        let mut v1 = seed.wrapping_add(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_2);
        let mut v2 = seed.wrapping_add(XXH_PRIME64_2);
        let mut v3 = seed;
        let mut v4 = seed.wrapping_sub(XXH_PRIME64_1);
        loop {
            v1 = xxh64_round(v1, read_le64_slice(&bytes[offset..offset + 8]));
            offset += 8;
            v2 = xxh64_round(v2, read_le64_slice(&bytes[offset..offset + 8]));
            offset += 8;
            v3 = xxh64_round(v3, read_le64_slice(&bytes[offset..offset + 8]));
            offset += 8;
            v4 = xxh64_round(v4, read_le64_slice(&bytes[offset..offset + 8]));
            offset += 8;
            if offset > limit {
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
    xxh64_finalize_bytes(h64, &bytes[offset..])
}

fn xxh64_core_h(seed: u64, bytes: &[u8]) -> u64 {
    let len = bytes.len();
    let mut h64: u64;
    let mut offset = 0usize;
    if len >= 32 {
        let limit = len - 32;
        let mut v1 = seed.wrapping_add(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_2);
        let mut v2 = seed.wrapping_sub(XXH_PRIME64_2);
        let mut v3 = seed.wrapping_add(XXH_PRIME64_3);
        let mut v4 = seed.wrapping_sub(XXH_PRIME64_1);
        loop {
            v1 = xxh64_round(v1, read_le64_slice(&bytes[offset..offset + 8]));
            offset += 8;
            v2 = xxh64_round(v2, read_le64_slice(&bytes[offset..offset + 8]));
            offset += 8;
            v3 = xxh64_round(v3, read_le64_slice(&bytes[offset..offset + 8]));
            offset += 8;
            v4 = xxh64_round(v4, read_le64_slice(&bytes[offset..offset + 8]));
            offset += 8;
            if offset > limit {
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
    xxh64_finalize_bytes(h64, &bytes[offset..])
}

fn value_bytes<T>(value: &T) -> &[u8] {
    unsafe { std::slice::from_raw_parts((value as *const T) as *const u8, mem::size_of::<T>()) }
}

// Function Definitions
pub fn xxh_get64bits(mem_ptr: &mut XXHU8) -> XXHU64 {
    xxh_read_le64_align(mem_ptr)
}
pub fn xxh_read_le64(mem_ptr: &mut XXHU8) -> XXHU64 {
    unsafe {
        let p = mem_ptr as *mut u8 as *const u8;
        let bytes = std::slice::from_raw_parts(p, 8);
        read_le64_slice(bytes)
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
    ((x << 24) & 0xff000000) | ((x << 8) & 0x00ff0000) | ((x >> 8) & 0x0000ff00) | ((x >> 24) & 0x000000ff)
}
pub fn xxh_read32(mem_ptr: &mut XXHU32) -> XXHU32 {
    *mem_ptr
}
pub fn xxh64_round(acc: XXHU64, input: XXHU64) -> XXHU64 {
    let mut acc = acc.wrapping_add(input.wrapping_mul(XXH_PRIME64_2));
    acc = acc.rotate_left(31);
    acc = acc.wrapping_mul(XXH_PRIME64_1);
    acc
}
pub fn xxh64_merge_round(acc: XXHU64, val: XXHU64) -> XXHU64 {
    let val = xxh64_round(0, val);
    let mut acc = acc ^ val;
    acc = acc.wrapping_mul(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_4);
    acc
}
pub fn xxh_get_32bits(ptr: &mut XXHU32) -> XXHU32 {
    xxh_read_le32_align(ptr)
}
pub fn xxh_read_le32_align(ptr: &mut XXHU32) -> XXHU32 {
    if xxh_is_little_endian() {
        xxh_read32(ptr)
    } else {
        let mut v = xxh_read32(ptr);
        xxh_swap32(&mut v)
    }
}
pub fn xxh64_avalanche(mut h64: XXHU64) -> XXHU64 {
    h64 ^= h64 >> 33;
    h64 = h64.wrapping_mul(XXH_PRIME64_2);
    h64 ^= h64 >> 29;
    h64 = h64.wrapping_mul(XXH_PRIME64_3);
    h64 ^= h64 >> 32;
    h64
}
pub fn xxh64_finalize(h64: XXHU64, ptr: &mut XXHU8, len: usize) -> XXHU64 {
    let n = len & 31;
    let base = ptr as *mut u8 as *const u8;
    let bytes = unsafe { std::slice::from_raw_parts(base, n) };
    xxh64_finalize_bytes(h64, bytes)
}
pub fn xxh64_endian_align(input: &mut XXHU8, len: usize, seed: XXHU64) -> XXHU64 {
    let base = input as *mut u8 as *const u8;
    let bytes = unsafe { std::slice::from_raw_parts(base, len) };
    xxh64_core(seed, bytes)
}
pub fn xxh64_endian_align_h(input: &mut XXHU8, len: usize, seed: XXHU64) -> XXHU64 {
    let base = input as *mut u8 as *const u8;
    let bytes = unsafe { std::slice::from_raw_parts(base, len) };
    xxh64_core_h(seed, bytes)
}
pub fn xxh64(input: *const u8, len: usize, seed: XXH64HashT) -> XXH64HashT {
    if input.is_null() || len == 0 {
        return xxh64_core(seed, &[]);
    }
    let bytes = unsafe { std::slice::from_raw_parts(input, len) };
    xxh64_core(seed, bytes)
}
pub fn xxh64_h(input: *const u8, len: usize, seed: XXH64HashT) -> XXH64HashT {
    if input.is_null() || len == 0 {
        return xxh64_core_h(seed, &[]);
    }
    let bytes = unsafe { std::slice::from_raw_parts(input, len) };
    xxh64_core_h(seed, bytes)
}
pub fn cset_hash1_callback(memptr: &mut XXHU8, size: usize) -> XXHU64 {
    let p = memptr as *mut u8 as *const u8;
    xxh64(p, size, CSET_DEFAULT_SEED)
}
pub fn cset_hash2_callback(memptr: &mut XXHU8, size: usize) -> XXHU64 {
    let p = memptr as *mut u8 as *const u8;
    xxh64_h(p, size, CSET_DEFAULT_SEED) | 1
}

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

impl<T: Copy + Default + PartialEq> Cset<T> {
    fn make_buckets(cap: usize) -> Vec<CsetValue<T>> {
        let mut v = Vec::with_capacity(cap);
        for _ in 0..cap {
            v.push(CsetValue { pi: 0, elem: T::default() });
        }
        v
    }

    pub fn new() -> Cset<T> {
        Cset {
            buckets: Self::make_buckets(CSET_INITIAL_CAP),
            max_load_factor: CSET_MAX_LOAD_FACTOR,
            min_load_factor: CSET_MIN_LOAD_FACTOR,
            seed: CSET_DEFAULT_SEED,
            v: CsetValue { pi: 0, elem: T::default() },
            bucket_size: 0,
            compare: None,
            temp_buckets: Vec::new(),
        }
    }

    pub fn empty(&self) -> bool {
        self.bucket_size == 0
    }

    pub fn tombstone(&self) -> bool {
        self.buckets.iter().any(|b| b.pi == -1)
    }

    pub fn index(&self, index: usize) -> T {
        self.buckets[index].elem
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
        // SAFETY: the C original exposes a raw mutable pointer to the
        // buckets vector regardless of the constness of `self`. We mirror
        // that by casting away the shared-reference restriction here; it
        // is the caller's responsibility to avoid data races, exactly as
        // in the original C macros.
        unsafe { &mut *(&self.buckets as *const Vec<CsetValue<T>> as *mut Vec<CsetValue<T>>) }
    }

    pub fn get_temp_buckets_ref(&self) -> &mut Vec<CsetValue<T>> {
        unsafe { &mut *(&self.temp_buckets as *const Vec<CsetValue<T>> as *mut Vec<CsetValue<T>>) }
    }

    pub fn size(&self) -> i32 {
        self.bucket_size as i32
    }

    pub fn capacity(&self) -> i32 {
        self.buckets.len() as i32
    }

    fn double_hash_index(h1: u64, h2: u64, i: usize, cap: usize) -> usize {
        (h1.wrapping_add((i as u64).wrapping_mul(h2)) % (cap as u64)) as usize
    }

    fn insert_into(
        buckets: &mut Vec<CsetValue<T>>,
        seed: u64,
        compare: &Option<fn(&T, &T) -> bool>,
        value: T,
    ) -> bool {
        let bytes = value_bytes(&value);
        let h1 = xxh64_core(seed, bytes);
        let h2 = xxh64_core_h(seed, bytes) | 1;
        let cap = buckets.len();
        let mut iteration: usize = 1;
        let mut index = 0usize;
        let mut found = false;
        loop {
            index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            if buckets[index].pi == 0 || buckets[index].pi == -1 {
                break;
            }
            let matches = match compare {
                Some(cmp) => cmp(&buckets[index].elem, &value),
                None => buckets[index].elem == value,
            };
            if matches {
                found = true;
                break;
            }
        }
        if !found {
            buckets[index].elem = value;
            buckets[index].pi = iteration as i32;
        }
        !found
    }

    fn resize(&mut self, new_cap: usize) {
        let mut new_buckets = Self::make_buckets(new_cap);
        let seed = self.seed;
        let compare = self.compare;
        for i in 0..self.buckets.len() {
            let pi = self.buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let value = self.buckets[i].elem;
            Self::insert_into(&mut new_buckets, seed, &compare, value);
        }
        self.buckets = new_buckets;
    }

    pub fn add(&mut self, value: T) -> i32 {
        let current_load_factor = self.bucket_size as f64 / self.buckets.len() as f64;
        if current_load_factor >= self.max_load_factor {
            let new_cap = self.buckets.len() * 2;
            self.resize(new_cap);
        }
        let seed = self.seed;
        let compare = self.compare;
        let inserted = Self::insert_into(&mut self.buckets, seed, &compare, value);
        if inserted {
            self.bucket_size += 1;
        }
        inserted as i32
    }

    pub fn remove(&mut self, value: T) -> i32 {
        let bytes = value_bytes(&value);
        let h1 = xxh64_core(self.seed, bytes);
        let h2 = xxh64_core_h(self.seed, bytes) | 1;
        let cap = self.buckets.len();
        let mut iteration: usize = 1;
        let mut index = 0usize;
        let mut found = false;
        loop {
            if iteration - 1 >= cap {
                break;
            }
            index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            if self.buckets[index].pi == -1 {
                continue;
            }
            if self.buckets[index].pi == 0 {
                break;
            }
            let matches = match self.compare {
                Some(cmp) => cmp(&self.buckets[index].elem, &value),
                None => self.buckets[index].elem == value,
            };
            if matches {
                found = true;
                break;
            }
        }
        if found {
            self.buckets[index].pi = -1;
            self.bucket_size -= 1;
        }
        found as i32
    }

    fn contains_ref(&self, value: &T) -> bool {
        let bytes = value_bytes(value);
        let h1 = xxh64_core(self.seed, bytes);
        let h2 = xxh64_core_h(self.seed, bytes) | 1;
        let cap = self.buckets.len();
        let mut iteration: usize = 1;
        let mut found = false;
        loop {
            if iteration - 1 >= cap {
                break;
            }
            let index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            if self.buckets[index].pi == -1 {
                continue;
            }
            if self.buckets[index].pi == 0 {
                break;
            }
            let matches = match self.compare {
                Some(cmp) => cmp(&self.buckets[index].elem, value),
                None => self.buckets[index].elem == *value,
            };
            if matches {
                found = true;
                break;
            }
        }
        found
    }

    pub fn contains(&mut self, value: &T) -> bool {
        self.contains_ref(value)
    }

    pub fn iter(&mut self) -> Vec<T> {
        self.buckets
            .iter()
            .filter(|b| b.pi != 0 && b.pi != -1)
            .map(|b| b.elem)
            .collect()
    }

    pub fn set_comparator(&mut self, compare: fn(&T, &T) -> bool) {
        self.compare = Some(compare);
    }

    pub fn clear(&mut self) {
        self.buckets = Self::make_buckets(CSET_INITIAL_CAP);
        self.bucket_size = 0;
    }

    pub fn intersect(&mut self, first: &Self, second: &Self) {
        for i in 0..first.buckets.len() {
            let pi = first.buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let value = first.buckets[i].elem;
            if second.contains_ref(&value) {
                self.add(value);
            }
        }
    }

    pub fn union(&mut self, first: &Self, second: &Self) {
        for i in 0..first.buckets.len() {
            let pi = first.buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let value = first.buckets[i].elem;
            self.add(value);
        }
        for i in 0..second.buckets.len() {
            let pi = second.buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let value = second.buckets[i].elem;
            self.add(value);
        }
    }

    pub fn is_disjoint(&mut self, other: &Self) -> bool {
        for i in 0..self.buckets.len() {
            let pi = self.buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let value = self.buckets[i].elem;
            if other.contains_ref(&value) {
                return false;
            }
        }
        true
    }

    pub fn difference(&mut self, first: &Self, second: &Self) {
        for i in 0..first.buckets.len() {
            let pi = first.buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let value = first.buckets[i].elem;
            if !second.contains_ref(&value) {
                self.add(value);
            }
        }
    }
}

impl<T: Copy + Default + PartialEq> Default for Cset<T> {
    fn default() -> Self {
        Self::new()
    }
}
