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

// --- internal helpers used by the xxh64 implementation ---

fn read_le64_slice(b: &[u8]) -> u64 {
    let mut r: u64 = 0;
    for i in 0..8 {
        r |= (b[i] as u64) << (8 * i);
    }
    r
}

fn read_le32_slice(b: &[u8]) -> u32 {
    let mut r: u32 = 0;
    for i in 0..4 {
        r |= (b[i] as u32) << (8 * i);
    }
    r
}

fn xxh64_finalize_slice(mut h64: u64, data: &[u8]) -> u64 {
    let mut len = data.len() & 31;
    let mut off = 0usize;
    while len >= 8 {
        let k1 = xxh64_round(0, read_le64_slice(&data[off..]));
        off += 8;
        h64 ^= k1;
        h64 = h64
            .rotate_left(27)
            .wrapping_mul(XXH_PRIME64_1)
            .wrapping_add(XXH_PRIME64_4);
        len -= 8;
    }
    if len >= 4 {
        h64 ^= (read_le32_slice(&data[off..]) as u64).wrapping_mul(XXH_PRIME64_1);
        off += 4;
        h64 = h64
            .rotate_left(23)
            .wrapping_mul(XXH_PRIME64_2)
            .wrapping_add(XXH_PRIME64_3);
        len -= 4;
    }
    while len > 0 {
        h64 ^= (data[off] as u64).wrapping_mul(XXH_PRIME64_5);
        off += 1;
        h64 = h64.rotate_left(11).wrapping_mul(XXH_PRIME64_1);
        len -= 1;
    }
    xxh64_avalanche(h64)
}

fn xxh64_core(data: &[u8], seed: u64, hvariant: bool) -> u64 {
    let len = data.len();
    let h64: u64;
    if len >= 32 {
        let mut v1 = seed.wrapping_add(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_2);
        let mut v2;
        let mut v3;
        let mut v4 = seed.wrapping_sub(XXH_PRIME64_1);
        if hvariant {
            v2 = seed.wrapping_sub(XXH_PRIME64_2);
            v3 = seed.wrapping_add(XXH_PRIME64_3);
        } else {
            v2 = seed.wrapping_add(XXH_PRIME64_2);
            v3 = seed;
        }
        let mut off = 0usize;
        while off + 32 <= len {
            v1 = xxh64_round(v1, read_le64_slice(&data[off..]));
            off += 8;
            v2 = xxh64_round(v2, read_le64_slice(&data[off..]));
            off += 8;
            v3 = xxh64_round(v3, read_le64_slice(&data[off..]));
            off += 8;
            v4 = xxh64_round(v4, read_le64_slice(&data[off..]));
            off += 8;
        }
        let mut hh = v1
            .rotate_left(1)
            .wrapping_add(v2.rotate_left(7))
            .wrapping_add(v3.rotate_left(12))
            .wrapping_add(v4.rotate_left(18));
        hh = xxh64_merge_round(hh, v1);
        hh = xxh64_merge_round(hh, v2);
        hh = xxh64_merge_round(hh, v3);
        hh = xxh64_merge_round(hh, v4);
        hh = hh.wrapping_add(len as u64);
        h64 = xxh64_finalize_slice(hh, &data[off..]);
    } else {
        let mut hh = if hvariant {
            seed.wrapping_add(XXH_PRIME64_1)
        } else {
            seed.wrapping_add(XXH_PRIME64_5)
        };
        hh = hh.wrapping_add(len as u64);
        h64 = xxh64_finalize_slice(hh, data);
    }
    h64
}

// Function Definitions
pub fn xxh_get64bits(mem_ptr: &mut XXHU8) -> XXHU64 {
    xxh_read_le64_align(mem_ptr)
}
pub fn xxh_read_le64(mem_ptr: &mut XXHU8) -> XXHU64 {
    unsafe {
        let b = std::slice::from_raw_parts(mem_ptr as *const u8, 8);
        read_le64_slice(b)
    }
}
pub fn xxh_is_little_endian() -> bool {
    let one: u32 = 1;
    one.to_ne_bytes()[0] == 1
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
    let mut acc = acc.wrapping_add(input.wrapping_mul(XXH_PRIME64_2));
    acc = acc.rotate_left(31);
    acc.wrapping_mul(XXH_PRIME64_1)
}
pub fn xxh64_merge_round(acc: XXHU64, val: XXHU64) -> XXHU64 {
    let val = xxh64_round(0, val);
    let acc = acc ^ val;
    acc.wrapping_mul(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_4)
}
pub fn xxh_get_32bits(ptr: &mut XXHU32) -> XXHU32 {
    xxh_read_le32_align(ptr)
}
pub fn xxh_read_le32_align(ptr: &mut XXHU32) -> XXHU32 {
    if xxh_is_little_endian() {
        xxh_read32(ptr)
    } else {
        xxh_swap32(&mut xxh_read32(ptr))
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
    let data = unsafe { std::slice::from_raw_parts(ptr as *const u8, len) };
    xxh64_finalize_slice(h64, data)
}
pub fn xxh64_endian_align(input: &mut XXHU8, len: usize, seed: XXHU64) -> XXHU64 {
    let data = unsafe { std::slice::from_raw_parts(input as *const u8, len) };
    xxh64_core(data, seed, false)
}
pub fn xxh64_endian_align_h(input: &mut XXHU8, len: usize, seed: XXHU64) -> XXHU64 {
    let data = unsafe { std::slice::from_raw_parts(input as *const u8, len) };
    xxh64_core(data, seed, true)
}
pub fn xxh64(input: *const u8, len: usize, seed: XXH64HashT) -> XXH64HashT {
    let data: &[u8] = if input.is_null() {
        &[]
    } else {
        unsafe { std::slice::from_raw_parts(input, len) }
    };
    xxh64_core(data, seed, false)
}
pub fn xxh64_h(input: *const u8, len: usize, seed: XXH64HashT) -> XXH64HashT {
    let data: &[u8] = if input.is_null() {
        &[]
    } else {
        unsafe { std::slice::from_raw_parts(input, len) }
    };
    xxh64_core(data, seed, true)
}
pub fn cset_hash1_callback(memptr: &mut XXHU8, size: usize) -> XXHU64 {
    let b = unsafe { std::slice::from_raw_parts(memptr as *const u8, size) };
    xxh64_core(b, CSET_DEFAULT_SEED, false)
}
pub fn cset_hash2_callback(memptr: &mut XXHU8, size: usize) -> XXHU64 {
    let b = unsafe { std::slice::from_raw_parts(memptr as *const u8, size) };
    xxh64_core(b, CSET_DEFAULT_SEED, true) | 1
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
impl<T> Cset<T> {
    fn empty_value() -> CsetValue<T> {
        CsetValue {
            pi: 0,
            elem: unsafe { mem::zeroed() },
        }
    }

    fn bytes_eq(a: &T, b: &T) -> bool {
        unsafe {
            let sa = std::slice::from_raw_parts(a as *const T as *const u8, mem::size_of::<T>());
            let sb = std::slice::from_raw_parts(b as *const T as *const u8, mem::size_of::<T>());
            sa == sb
        }
    }

    fn double_hash_index(h1: u64, h2: u64, i: usize, cap: usize) -> usize {
        (h1.wrapping_add((i as u64).wrapping_mul(h2)) % (cap as u64)) as usize
    }

    fn hash1(&self, value: &T) -> u64 {
        let bytes =
            unsafe { std::slice::from_raw_parts(value as *const T as *const u8, mem::size_of::<T>()) };
        xxh64(bytes.as_ptr(), bytes.len(), self.seed)
    }

    fn hash2(&self, value: &T) -> u64 {
        let bytes =
            unsafe { std::slice::from_raw_parts(value as *const T as *const u8, mem::size_of::<T>()) };
        xxh64_h(bytes.as_ptr(), bytes.len(), self.seed) | 1
    }

    fn matches_at(&self, index: usize, value: &T) -> bool {
        if let Some(cmp) = self.compare {
            cmp(&self.buckets[index].elem, value)
        } else {
            Self::bytes_eq(&self.buckets[index].elem, value)
        }
    }

    fn contains_inner(&self, value: &T) -> bool {
        let h1 = self.hash1(value);
        let cap = self.buckets.len();
        let mut iteration = 1usize;
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
            if self.matches_at(index, value) {
                found = true;
                break;
            }
        }
        found
    }

    fn add_(&mut self, value: T) -> i32 {
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
            if self.matches_at(index, &value) {
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

    fn resize(&mut self, cap: usize) {
        let mut newbuckets = Vec::with_capacity(cap);
        for _ in 0..cap {
            newbuckets.push(Self::empty_value());
        }
        let old = std::mem::replace(&mut self.buckets, newbuckets);
        self.bucket_size = 0;
        for item in old.into_iter() {
            if item.pi == 0 || item.pi == -1 {
                continue;
            }
            self.add_(item.elem);
        }
    }

    pub fn new() -> Cset<T> {
        let mut buckets = Vec::with_capacity(CSET_INITIAL_CAP);
        for _ in 0..CSET_INITIAL_CAP {
            buckets.push(Self::empty_value());
        }
        Cset {
            buckets,
            max_load_factor: CSET_MAX_LOAD_FACTOR,
            min_load_factor: CSET_MIN_LOAD_FACTOR,
            seed: CSET_DEFAULT_SEED,
            v: Self::empty_value(),
            bucket_size: 0,
            compare: None,
            temp_buckets: Vec::new(),
        }
    }
    pub fn empty(&self) -> bool {
        self.v.pi == 0
    }
    pub fn tombstone(&self) -> bool {
        self.v.pi == -1
    }
    pub fn index(&self, index: usize) -> T {
        unsafe { ptr::read(&self.buckets[index].elem) }
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
        let p = &self.buckets as *const Vec<CsetValue<T>> as *mut Vec<CsetValue<T>>;
        unsafe { &mut *p }
    }
    pub fn get_temp_buckets_ref(&self) -> &mut Vec<CsetValue<T>> {
        let p = &self.temp_buckets as *const Vec<CsetValue<T>> as *mut Vec<CsetValue<T>>;
        unsafe { &mut *p }
    }
    pub fn size(&self) -> i32 {
        self.bucket_size as i32
    }
    pub fn capacity(&self) -> i32 {
        self.buckets.len() as i32
    }
    pub fn add(&mut self, value: T) -> i32 {
        let current_load_factor = self.bucket_size as f64 / self.buckets.len() as f64;
        if current_load_factor >= self.max_load_factor {
            let newcap = self.buckets.len() * 2;
            self.resize(newcap);
        }
        self.add_(value)
    }
    pub fn remove(&mut self, value: T) -> i32 {
        let h1 = self.hash1(&value);
        let cap = self.buckets.len();
        let mut iteration = 1usize;
        let mut index = 0usize;
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
            if self.matches_at(index, &value) {
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
    pub fn contains(&mut self, value: &T) -> bool {
        self.contains_inner(value)
    }
    pub fn iter(&mut self) -> Vec<T> {
        let mut result = Vec::new();
        for item in self.buckets.iter() {
            if item.pi == 0 || item.pi == -1 {
                continue;
            }
            result.push(unsafe { ptr::read(&item.elem) });
        }
        result
    }
    pub fn set_comparator(&mut self, compare: fn(&T, &T) -> bool) {
        self.compare = Some(compare);
    }
    pub fn clear(&mut self) {
        let mut buckets = Vec::with_capacity(CSET_INITIAL_CAP);
        for _ in 0..CSET_INITIAL_CAP {
            buckets.push(Self::empty_value());
        }
        self.buckets = buckets;
        self.bucket_size = 0;
    }
    pub fn intersect(&mut self, first: &Self, second: &Self) {
        for item in first.buckets.iter() {
            if item.pi == 0 || item.pi == -1 {
                continue;
            }
            let value = unsafe { ptr::read(&item.elem) };
            if second.contains_inner(&value) {
                self.add(value);
            }
        }
    }
    pub fn union(&mut self, first: &Self, second: &Self) {
        for item in first.buckets.iter() {
            if item.pi == 0 || item.pi == -1 {
                continue;
            }
            let value = unsafe { ptr::read(&item.elem) };
            self.add(value);
        }
        for item in second.buckets.iter() {
            if item.pi == 0 || item.pi == -1 {
                continue;
            }
            let value = unsafe { ptr::read(&item.elem) };
            self.add(value);
        }
    }
    pub fn is_disjoint(&mut self, other: &Self) -> bool {
        for item in self.buckets.iter() {
            if item.pi == 0 || item.pi == -1 {
                continue;
            }
            let value = unsafe { ptr::read(&item.elem) };
            if other.contains_inner(&value) {
                return false;
            }
        }
        true
    }
    pub fn difference(&mut self, first: &Self, second: &Self) {
        for item in first.buckets.iter() {
            if item.pi == 0 || item.pi == -1 {
                continue;
            }
            let value = unsafe { ptr::read(&item.elem) };
            if !second.contains_inner(&value) {
                self.add(value);
            }
        }
    }
}
