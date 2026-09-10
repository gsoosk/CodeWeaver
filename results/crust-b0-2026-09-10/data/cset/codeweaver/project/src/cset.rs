// Import necessary modules
use std::cell::UnsafeCell;
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
// Function Definitions
pub fn xxh_get64bits(mem_ptr: &mut XXHU8) -> XXHU64 {
    xxh_read_le64_align(mem_ptr)
}
pub fn xxh_read_le64(mem_ptr: &mut XXHU8) -> XXHU64 {
    // The C source walks past the single `xxh_u8` behind `memPtr` as an
    // 8-byte little-endian buffer. `u8` has alignment 1, so raw-pointer
    // arithmetic over `*const u8` is always sound here.
    unsafe {
        let byte_ptr = mem_ptr as *mut XXHU8 as *const XXHU8;
        (*byte_ptr as XXHU64)
            | ((*byte_ptr.add(1) as XXHU64) << 8)
            | ((*byte_ptr.add(2) as XXHU64) << 16)
            | ((*byte_ptr.add(3) as XXHU64) << 24)
            | ((*byte_ptr.add(4) as XXHU64) << 32)
            | ((*byte_ptr.add(5) as XXHU64) << 40)
            | ((*byte_ptr.add(6) as XXHU64) << 48)
            | ((*byte_ptr.add(7) as XXHU64) << 56)
    }
}
pub fn xxh_is_little_endian() -> bool {
    1u32.to_ne_bytes()[0] == 1
}
pub fn xxh_read_le64_align(mem_ptr: &mut XXHU8) -> XXHU64 {
    xxh_read_le64(mem_ptr)
}
pub fn xxh_swap32(x: &mut  XXHU32) -> XXHU32 {
    let v = *x;
    ((v << 24) & 0xff000000)
        | ((v << 8) & 0x00ff0000)
        | ((v >> 8) & 0x0000ff00)
        | ((v >> 24) & 0x000000ff)
}
pub fn xxh_read32(mem_ptr: &mut XXHU32) -> XXHU32 {
    // Equivalent to the C `memcpy(&val, memPtr, sizeof(val))`: read 4 raw
    // bytes at this address, unaligned-safe, into a u32 without relying on
    // the pointee's actual alignment.
    unsafe {
        let byte_ptr = mem_ptr as *mut XXHU32 as *const u8;
        ptr::read_unaligned(byte_ptr as *const XXHU32)
    }
}
pub fn xxh64_round(acc: XXHU64, input: XXHU64) -> XXHU64 {
    let acc = acc.wrapping_add(input.wrapping_mul(XXH_PRIME64_2));
    let acc = acc.rotate_left(31);
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
pub fn xxh64_finalize(mut h64: XXHU64, ptr: &mut XXHU8, len: usize) -> XXHU64 {
    let mut len = len & 31;
    // Raw pointer advance over an arbitrary-length byte buffer, mirroring
    // the C `ptr++`/`ptr += n` walk; confined to this function.
    unsafe {
        let mut p = ptr as *mut XXHU8;
        while len >= 8 {
            let k1 = xxh64_round(0, xxh_get64bits(&mut *p));
            p = p.add(8);
            h64 ^= k1;
            h64 = h64.rotate_left(27).wrapping_mul(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_4);
            len -= 8;
        }
        if len >= 4 {
            let bits = xxh_get_32bits(&mut *(p as *mut XXHU32));
            h64 ^= (bits as XXHU64).wrapping_mul(XXH_PRIME64_1);
            p = p.add(4);
            h64 = h64.rotate_left(23).wrapping_mul(XXH_PRIME64_2).wrapping_add(XXH_PRIME64_3);
            len -= 4;
        }
        while len > 0 {
            h64 ^= (*p as XXHU64).wrapping_mul(XXH_PRIME64_5);
            p = p.add(1);
            h64 = h64.rotate_left(11).wrapping_mul(XXH_PRIME64_1);
            len -= 1;
        }
    }
    xxh64_avalanche(h64)
}
pub fn xxh64_endian_align(input: &mut XXHU8, len: usize, seed: XXHU64) -> XXHU64 {
    // Raw pointer walk over the caller's byte buffer, mirroring the C
    // `const xxh_u8 *input` advance in the 32-byte block loop; confined to
    // this function like the other xxhash primitives above.
    unsafe {
        let mut p = input as *mut XXHU8;
        let mut h64: XXHU64;
        if len >= 32 {
            let b_end = p.add(len);
            let limit = b_end.sub(32);
            let mut v1 = seed.wrapping_add(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_2);
            let mut v2 = seed.wrapping_add(XXH_PRIME64_2);
            let mut v3 = seed;
            let mut v4 = seed.wrapping_sub(XXH_PRIME64_1);
            loop {
                v1 = xxh64_round(v1, xxh_get64bits(&mut *p));
                p = p.add(8);
                v2 = xxh64_round(v2, xxh_get64bits(&mut *p));
                p = p.add(8);
                v3 = xxh64_round(v3, xxh_get64bits(&mut *p));
                p = p.add(8);
                v4 = xxh64_round(v4, xxh_get64bits(&mut *p));
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
        h64 = h64.wrapping_add(len as XXHU64);
        xxh64_finalize(h64, &mut *p, len)
    }
}
pub fn xxh64_endian_align_h(input: &mut XXHU8, len: usize, seed: XXHU64) -> XXHU64 {
    // Independently seeded variant used for the second hash callback;
    // note the distinct v2/v3/v4 seeding and else-branch prime from
    // `xxh64_endian_align`.
    unsafe {
        let mut p = input as *mut XXHU8;
        let mut h64: XXHU64;
        if len >= 32 {
            let b_end = p.add(len);
            let limit = b_end.sub(32);
            let mut v1 = seed.wrapping_add(XXH_PRIME64_1).wrapping_add(XXH_PRIME64_2);
            let mut v2 = seed.wrapping_sub(XXH_PRIME64_2);
            let mut v3 = seed.wrapping_add(XXH_PRIME64_3);
            let mut v4 = seed.wrapping_sub(XXH_PRIME64_1);
            loop {
                v1 = xxh64_round(v1, xxh_get64bits(&mut *p));
                p = p.add(8);
                v2 = xxh64_round(v2, xxh_get64bits(&mut *p));
                p = p.add(8);
                v3 = xxh64_round(v3, xxh_get64bits(&mut *p));
                p = p.add(8);
                v4 = xxh64_round(v4, xxh_get64bits(&mut *p));
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
        h64 = h64.wrapping_add(len as XXHU64);
        xxh64_finalize(h64, &mut *p, len)
    }
}
pub fn xxh64(input: *const u8, len: usize, seed: XXH64HashT) -> XXH64HashT {
    // `input` stands in for the C `const void *`; the underlying reference
    // is only ever produced from an already-valid `&mut u8`/byte buffer by
    // callers (see cset_hash1_callback below), matching how the earlier
    // xxhash primitives treat `&mut XXHU8` as a raw memory location.
    unsafe {
        let ptr = input as *mut XXHU8;
        xxh64_endian_align(&mut *ptr, len, seed)
    }
}
pub fn xxh64_h(input: *const u8, len: usize, seed: XXH64HashT) -> XXH64HashT {
    unsafe {
        let ptr = input as *mut XXHU8;
        xxh64_endian_align_h(&mut *ptr, len, seed)
    }
}
pub fn cset_hash1_callback(memptr: &mut XXHU8, size: usize) -> XXHU64 {
    xxh64(memptr as *const XXHU8, size, CSET_DEFAULT_SEED)
}
pub fn cset_hash2_callback(memptr: &mut XXHU8, size: usize) -> XXHU64 {
    xxh64_h(memptr as *const XXHU8, size, CSET_DEFAULT_SEED) | 1
}
pub struct  CsetValue<T> {
    pi: i32, 
    elem: T, 
}
pub struct Cset<T> {
    // Wrapped in `UnsafeCell` (rather than a plain `Vec`) solely so that
    // `get_buckets_ref`/`get_temp_buckets_ref` can hand out a `&mut Vec<..>`
    // from a `&self` method -- mirroring the C macros
    // (`cset__vector_buckets_ref`/`cset__vector_temp_buckets_ref`), which
    // return a mutable pointer into the struct regardless of the calling
    // context's constness. Casting `&T` to `&mut T` directly is undefined
    // behavior in Rust; `UnsafeCell` is the sound way to allow this
    // shared-mutable access pattern. Only `Cset<T>`'s own methods ever call
    // these accessors, and never alias the resulting `&mut Vec<..>` with
    // another live reference to the same field.
    buckets: UnsafeCell<Vec<CsetValue<T>>>,
    max_load_factor: f64,                                                   
    min_load_factor: f64,                                                    
    seed: u64,                                                          
    v: CsetValue<T>,                                                        
    bucket_size: usize, 
    compare: Option<fn(&T, &T) -> bool>, 
    temp_buckets: UnsafeCell<Vec<CsetValue<T>>>,
}
impl<T: Clone> Cset<T> {
    pub fn new() -> Cset<T> {
        // Mirrors `cset__init`: allocate `CSET_INITIAL_CAP` buckets and
        // force-initialize every slot's `pi` to 0 (empty), exactly like the
        // `CSET__FORCE_INITIALIZE` loop in the C macro. The C struct embeds
        // a real `cset_type_ v` field (and the bucket vector is pre-sized
        // with real, if garbage, element storage from `malloc`) without
        // requiring any particular value of the element type; we mirror
        // that "value not yet meaningful until written" property here via
        // zeroed memory rather than requiring `T: Default`. This is sound
        // for the plain-data types (`i32`, `char`, simple structs) this
        // container is instantiated with in the tests, matching the C
        // behavior of uninitialized-but-never-read element bytes until a
        // slot's `pi` marks it occupied.
        let mut buckets = Vec::with_capacity(CSET_INITIAL_CAP);
        for _ in 0..CSET_INITIAL_CAP {
            let elem = unsafe { mem::MaybeUninit::<T>::zeroed().assume_init() };
            buckets.push(CsetValue { pi: 0, elem });
        }
        let v_elem = unsafe { mem::MaybeUninit::<T>::zeroed().assume_init() };
        Cset {
            buckets: UnsafeCell::new(buckets),
            max_load_factor: CSET_MAX_LOAD_FACTOR,
            min_load_factor: CSET_MIN_LOAD_FACTOR,
            seed: CSET_DEFAULT_SEED,
            v: CsetValue { pi: 0, elem: v_elem },
            bucket_size: 0,
            compare: None,
            temp_buckets: UnsafeCell::new(Vec::new()),
        }
    }
    // Public, no-index convenience predicates over the staged `self.v`
    // slot (the scaffold declares `empty`/`tombstone` without an index
    // parameter, unlike the C `cset__empty`/`cset__tombstone` macros which
    // take a vector+index). The actual per-bucket state checks used
    // internally by add/remove/contains/resize/iter are the private
    // `empty_at`/`tombstone_at` helpers below, which mirror the C macros
    // exactly.
    pub fn empty(&self) -> bool {
        self.v.pi == 0
    }
    pub fn tombstone(&self) -> bool {
        self.v.pi == -1
    }
    // Private index-taking helpers mirroring `cset__empty`/`cset__tombstone`.
    fn empty_at(&self, index: usize) -> bool {
        let buckets = unsafe { &*self.buckets.get() };
        buckets[index].pi == 0
    }
    fn tombstone_at(&self, index: usize) -> bool {
        let buckets = unsafe { &*self.buckets.get() };
        buckets[index].pi == -1
    }
    pub fn index(&self, index: usize) -> T {
        // Mirrors `cset__index`: returns (a clone of) the element stored at
        // `index`, regardless of that slot's occupancy state.
        let buckets = self.get_buckets_ref();
        buckets[index].elem.clone()
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
    pub fn set_seed(&mut self, seed: u64){
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
        unsafe { &*self.buckets.get() }
    }
    pub fn get_buckets_ref(&self) -> &mut Vec<CsetValue<T>> {
        // The C counterpart (`cset__vector_buckets_ref`) returns a raw
        // pointer to the embedded vector regardless of the enclosing
        // macro's constness, and callers (add/remove/contains/resize)
        // mutate through it in place. `buckets` is stored in an
        // `UnsafeCell`, so dereferencing its raw pointer into a `&mut`
        // here is sound interior mutability (unlike casting `&T` to
        // `&mut T` directly, which is UB); this is safe in practice
        // because `Cset<T>`'s own methods are the only callers and never
        // alias this mutable reference with another live reference to
        // `buckets` at the same time.
        unsafe { &mut *self.buckets.get() }
    }
    pub fn get_temp_buckets_ref(&self) -> &mut Vec<CsetValue<T>> {
        unsafe { &mut *self.temp_buckets.get() }
    }
    pub fn size(&self) -> i32 {
        self.bucket_size as i32
    }
    pub fn capacity(&self) -> i32 {
        let buckets = unsafe { &*self.buckets.get() };
        buckets.len() as i32
    }
    // Mirrors `cset__h1hash`/`cset__h2hash`'s default (no-customhasher)
    // branch: `XXH64`/`XXH64_h` over the raw bytes of `value` (sizeof(T)),
    // seeded with `self.seed`. The scaffold has no `customhasher` field, so
    // this is the only path (matches `plan.json`'s documented scaffold gap).
    fn hash_pair(&self, value: &T) -> (XXHU64, XXHU64) {
        let size = mem::size_of::<T>();
        let ptr = value as *const T as *const u8;
        let h1 = xxh64(ptr, size, self.seed);
        let h2 = xxh64_h(ptr, size, self.seed) | 1;
        (h1, h2)
    }
    // Mirrors `cset__double_hash_index`: (h1 + i*h2) % cap.
    fn double_hash_index(h1: XXHU64, h2: XXHU64, i: usize, cap: usize) -> usize {
        ((h1.wrapping_add((i as XXHU64).wrapping_mul(h2))) % (cap as XXHU64)) as usize
    }
    // Mirrors `cset__bytes_compare`: raw byte-for-byte equality over
    // sizeof(T), used when no custom comparator has been installed.
    fn bytes_equal(a: &T, b: &T) -> bool {
        let size = mem::size_of::<T>();
        unsafe {
            let pa = std::slice::from_raw_parts(a as *const T as *const u8, size);
            let pb = std::slice::from_raw_parts(b as *const T as *const u8, size);
            pa == pb
        }
    }
    // Mirrors `cset__matches`: dispatch to `self.compare` if set, else fall
    // back to raw byte-equality.
    fn matches_elem(&self, existing: &T, value: &T) -> bool {
        match self.compare {
            Some(f) => f(existing, value),
            None => Self::bytes_equal(existing, value),
        }
    }
    // Mirrors `cset__resize`: rehash every live (non-empty, non-tombstone)
    // element into a fresh `new_cap`-sized bucket vector (dropping
    // tombstones by omission), then swap it in. Needed so `add`'s
    // load-factor check has a real resize to call instead of a no-op stub:
    // with `CSET_INITIAL_CAP == 2`, inserting a 3rd distinct element with a
    // stub resize would probe forever (both slots permanently occupied).
    fn resize(&mut self, new_cap: usize) {
        let mut new_buckets = Vec::with_capacity(new_cap);
        for _ in 0..new_cap {
            let elem = unsafe { mem::MaybeUninit::<T>::zeroed().assume_init() };
            new_buckets.push(CsetValue { pi: 0, elem });
        }
        let old_buckets = mem::replace(self.get_buckets_ref(), new_buckets);
        let mut new_size: usize = 0;
        for old in old_buckets.into_iter() {
            if old.pi == 0 || old.pi == -1 {
                // empty or tombstone: drop it during the rehash.
                continue;
            }
            let elem = old.elem;
            let (h1, h2) = self.hash_pair(&elem);
            let mut iteration: usize = 1;
            loop {
                let index = Self::double_hash_index(h1, h2, iteration - 1, new_cap);
                iteration += 1;
                let is_open = {
                    let buckets = self.get_buckets_ref();
                    buckets[index].pi == 0 || buckets[index].pi == -1
                };
                if is_open {
                    let buckets = self.get_buckets_ref();
                    buckets[index].elem = elem;
                    buckets[index].pi = iteration as i32;
                    break;
                }
            }
            new_size += 1;
        }
        self.bucket_size = new_size;
    }
    pub fn add(&mut self, value: T) -> i32 {
        // Mirrors `cset__add`'s pre-insert load-factor check.
        let cap = self.capacity() as usize;
        if cap > 0 {
            let current_load_factor = self.bucket_size as f64 / cap as f64;
            if current_load_factor >= self.max_load_factor {
                self.resize(cap * 2);
            }
        }
        let cap = self.capacity() as usize;
        // Mirrors `cset__add_`: probe via double hashing, breaking
        // unconditionally at the first empty-or-tombstone slot (not
        // scanning the whole table for a later duplicate); only slots
        // visited before that break are checked for equality.
        let (h1, h2) = self.hash_pair(&value);
        let mut iteration: usize = 1;
        let mut index: usize;
        let mut found = false;
        loop {
            index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            let is_open = self.empty_at(index) || self.tombstone_at(index);
            if is_open {
                break;
            }
            let is_match = {
                let buckets = self.get_buckets_ref();
                self.matches_elem(&buckets[index].elem, &value)
            };
            if is_match {
                found = true;
                break;
            }
        }
        if !found {
            {
                let buckets = self.get_buckets_ref();
                buckets[index].elem = value;
                buckets[index].pi = iteration as i32;
            }
            self.bucket_size += 1;
        }
        self.bucket_size as i32
    }
    pub fn remove(&mut self, value: T) -> i32 {
        // Mirrors `cset__remove_`: probe with the same double-hash sequence
        // as add/contains, skipping tombstones, stopping at the first
        // empty slot or a match; on match, tombstone the slot (pi=-1) and
        // decrement bucket_size. No-op if not found.
        let cap = self.capacity() as usize;
        if cap == 0 {
            return self.bucket_size as i32;
        }
        let (h1, h2) = self.hash_pair(&value);
        let mut iteration: usize = 1;
        let mut index: usize = 0;
        let mut found = false;
        loop {
            if iteration - 1 >= cap {
                break;
            }
            index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            if self.tombstone_at(index) {
                continue;
            }
            if self.empty_at(index) {
                break;
            }
            let is_match = {
                let buckets = self.get_buckets_ref();
                self.matches_elem(&buckets[index].elem, &value)
            };
            if is_match {
                found = true;
                break;
            }
        }
        if found {
            let buckets = self.get_buckets_ref();
            buckets[index].pi = -1;
            self.bucket_size -= 1;
        }
        self.bucket_size as i32
    }
    pub fn contains(&mut self, value: &T) -> bool {
        self.contains_ref(value)
    }
    // Read-only core of `contains`; the scaffold declares `contains` as
    // `&mut self` (matching the C macro's non-const `cset` pointer), but
    // the probe never mutates any field, so a `&self` helper lets
    // intersect/union/is_disjoint/difference call it on `&Self` borrows of
    // `first`/`second`/`other` without an unsound `&T` -> `&mut T` cast.
    fn contains_ref(&self, value: &T) -> bool {
        // Mirrors `cset__contains_`: probe up to `cap` iterations, skipping
        // tombstones, stopping at the first empty slot or a match.
        let cap = self.capacity() as usize;
        if cap == 0 {
            return false;
        }
        let (h1, h2) = self.hash_pair(value);
        let mut iteration: usize = 1;
        let mut found = false;
        loop {
            if iteration - 1 >= cap {
                break;
            }
            let index = Self::double_hash_index(h1, h2, iteration - 1, cap);
            iteration += 1;
            if self.tombstone_at(index) {
                continue;
            }
            if self.empty_at(index) {
                break;
            }
            let is_match = {
                let buckets = self.get_buckets_ref();
                self.matches_elem(&buckets[index].elem, value)
            };
            if is_match {
                found = true;
                break;
            }
        }
        found
    }
    pub fn iter(&mut self) -> Vec<T> {
        // Mirrors `cset_iterator__init/__done/__next`: walk buckets in
        // array order, skip empty/tombstone slots, collect live elements
        // in bucket order (not insertion order). Bounded by bucket_size,
        // matching `cset_iterator__done`'s `current_count >= size` check.
        let mut result = Vec::with_capacity(self.bucket_size);
        let buckets = self.get_buckets_ref();
        let mut current_index = 0usize;
        let mut current_count = 0usize;
        while current_count < self.bucket_size && current_index < buckets.len() {
            let pi = buckets[current_index].pi;
            if pi == 0 || pi == -1 {
                current_index += 1;
                continue;
            }
            result.push(buckets[current_index].elem.clone());
            current_count += 1;
            current_index += 1;
        }
        result
    }
    pub fn set_comparator(&mut self, compare: fn(&T, &T) -> bool) {
        // Mirrors `cset__set_comparator`: store the fn pointer; add/remove/
        // contains dispatch to it via `matches_elem` instead of the default
        // raw-byte equality.
        self.compare = Some(compare);
    }
    pub fn clear(&mut self) {
        // Mirrors `cset__clear`: reset to CSET_INITIAL_CAP freshly zeroed
        // buckets and bucket_size=0. The old Vec is dropped automatically
        // when replaced (Rust ownership stands in for `cset__free`).
        let mut new_buckets = Vec::with_capacity(CSET_INITIAL_CAP);
        for _ in 0..CSET_INITIAL_CAP {
            let elem = unsafe { mem::MaybeUninit::<T>::zeroed().assume_init() };
            new_buckets.push(CsetValue { pi: 0, elem });
        }
        *self.get_buckets_ref() = new_buckets;
        self.bucket_size = 0;
    }
    pub fn intersect(&mut self, first: &Self, second: &Self) {
        // Mirrors `cset__intersect`: for each occupied element of `first`
        // that is also contained in `second`, add() it into `self` (self
        // is not cleared first).
        let first_buckets = first.get_buckets_ref();
        let cap = first_buckets.len();
        for i in 0..cap {
            let pi = first_buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let elem = first_buckets[i].elem.clone();
            if second.contains_ref(&elem) {
                self.add(elem);
            }
        }
    }
    pub fn union(&mut self, first: &Self, second: &Self) {
        // Mirrors `cset__union`: add() every occupied element of `first`,
        // then every occupied element of `second`, into `self`.
        let first_buckets = first.get_buckets_ref();
        for i in 0..first_buckets.len() {
            let pi = first_buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let elem = first_buckets[i].elem.clone();
            self.add(elem);
        }
        let second_buckets = second.get_buckets_ref();
        for i in 0..second_buckets.len() {
            let pi = second_buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let elem = second_buckets[i].elem.clone();
            self.add(elem);
        }
    }
    pub fn is_disjoint(&mut self, other: &Self) -> bool {
        // Mirrors `cset__is_disjoint`: return false as soon as any occupied
        // element of `self` is contained() in `other` (early exit); true
        // otherwise.
        let self_buckets = self.get_buckets_ref();
        let cap = self_buckets.len();
        for i in 0..cap {
            let pi = self_buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let elem = self_buckets[i].elem.clone();
            if other.contains_ref(&elem) {
                return false;
            }
        }
        true
    }
    pub fn difference(&mut self, first: &Self, second: &Self) {
        // Mirrors `cset__difference`: add() each occupied element of
        // `first` that is NOT contained in `second`.
        let first_buckets = first.get_buckets_ref();
        for i in 0..first_buckets.len() {
            let pi = first_buckets[i].pi;
            if pi == 0 || pi == -1 {
                continue;
            }
            let elem = first_buckets[i].elem.clone();
            if !second.contains_ref(&elem) {
                self.add(elem);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Behavioral unit tests (Part B). Mirrors README.md's assert()-driven C
// examples 1:1 onto the public Cset<T> API. No mockable I/O boundary exists
// in the source (pure in-memory data structure), so the only "mock/fixture"
// seam needed is the `Node`-style struct + custom comparator fn used by the
// README's custom-hash/comparator example (M6/M7).
//
// All bodies are stubs (`todo!()`) for the Translator milestone steps to
// fill in; #[ignore] keeps them out of the default `cargo test` run so this
// skeleton stays green until each milestone lands. Remove #[ignore] as each
// milestone's tests are implemented.
#[cfg(test)]
mod tests {
    use super::*;

    // Mock/fixture: mirrors README's `Node { x, y }` + `custom_comparator`,
    // used only to exercise M6/M7 comparator-dispatch (no custom-hasher
    // field exists in the scaffold, so only the comparator half applies).
    #[derive(Clone, Copy)]
    struct Node {
        x: i32,
        y: i32,
    }

    fn node_comparator(self_: &Node, other: &Node) -> bool {
        // Mirrors README's custom_comparator: dedupe by `x` only.
        self_.x == other.x
    }

    // --- M1: xxhash byte-reading and mixing primitives ---------------------
    #[test]
    fn test_xxh_is_little_endian_matches_platform() {
        assert_eq!(xxh_is_little_endian(), 1u32.to_ne_bytes()[0] == 1);
    }

    #[test]
    fn test_xxh_read_le64_round_trip() {
        let mut bytes: [u8; 8] = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08];
        let val = xxh_read_le64(&mut bytes[0]);
        assert_eq!(val, 0x0807060504030201u64);
    }

    #[test]
    fn test_xxh_swap32_reverses_bytes() {
        let mut x: u32 = 0x01020304;
        assert_eq!(xxh_swap32(&mut x), 0x04030201);
    }

    #[test]
    fn test_xxh64_round_is_deterministic() {
        let a = xxh64_round(0, 42);
        let b = xxh64_round(0, 42);
        assert_eq!(a, b);
    }

    #[test]
    fn test_xxh64_avalanche_changes_value() {
        assert_ne!(xxh64_avalanche(42), 42);
    }

    #[test]
    fn test_xxh64_finalize_short_tail() {
        let mut bytes: [u8; 3] = [0xAA, 0xBB, 0xCC];
        let h1 = xxh64_finalize(0, &mut bytes[0], 3);
        let h2 = xxh64_finalize(0, &mut bytes[0], 3);
        assert_eq!(h1, h2);
    }

    #[test]
    fn test_xxh64_known_answer_empty_input() {
        // Short (< 32 byte) input exercises the `else` seeding branch and
        // the tail loop of finalize; must be deterministic across calls.
        let mut bytes: [u8; 3] = [0xAA, 0xBB, 0xCC];
        let h1 = xxh64(bytes.as_ptr(), 3, CSET_DEFAULT_SEED);
        let h2 = xxh64(bytes.as_ptr(), 3, CSET_DEFAULT_SEED);
        assert_eq!(h1, h2);
        assert_ne!(h1, 0);
    }

    #[test]
    fn test_xxh64_known_answer_long_input() {
        // >32-byte input exercises the v1..v4 block-mixing loop.
        let mut bytes: [u8; 40] = [0u8; 40];
        for (i, b) in bytes.iter_mut().enumerate() {
            *b = i as u8;
        }
        let h1 = xxh64(bytes.as_ptr(), 40, CSET_DEFAULT_SEED);
        let h2 = xxh64(bytes.as_ptr(), 40, CSET_DEFAULT_SEED);
        assert_eq!(h1, h2);
        // Different seed must (overwhelmingly likely) produce a different hash.
        let h3 = xxh64(bytes.as_ptr(), 40, CSET_DEFAULT_SEED.wrapping_add(1));
        assert_ne!(h1, h3);
    }

    // --- M2: xxh64_h / cset hash callbacks ----------------------------------
    #[test]
    fn test_cset_hash2_callback_always_odd() {
        let mut bytes: [u8; 4] = [1, 2, 3, 4];
        for len in 1..=4usize {
            let h2 = cset_hash2_callback(&mut bytes[0], len);
            assert_eq!(h2 & 1, 1, "hash2 must always be forced odd");
        }
    }

    #[test]
    fn test_hash1_and_hash2_are_independent() {
        let mut bytes: [u8; 8] = [10, 20, 30, 40, 50, 60, 70, 80];
        let h1 = cset_hash1_callback(&mut bytes[0], 8);
        let h2 = cset_hash2_callback(&mut bytes[0], 8);
        assert_ne!(h1, h2);
        // Both are deterministic given the same input.
        let h1_again = cset_hash1_callback(&mut bytes[0], 8);
        let h2_again = cset_hash2_callback(&mut bytes[0], 8);
        assert_eq!(h1, h1_again);
        assert_eq!(h2, h2_again);
    }

    // --- M3: Cset::new() and field accessors --------------------------------
    #[test]
    fn test_new_default_state() {
        let set: Cset<i32> = Cset::new();
        assert_eq!(set.size(), 0);
        assert_eq!(set.capacity(), CSET_INITIAL_CAP as i32);
        assert_eq!(set.get_size(), 0);
        assert_eq!(set.get_seed(), CSET_DEFAULT_SEED);
        assert_eq!(set.get_max_load_factor(), CSET_MAX_LOAD_FACTOR);
        assert_eq!(set.get_min_load_factor(), CSET_MIN_LOAD_FACTOR);
        assert_eq!(set.get_buckets().len(), CSET_INITIAL_CAP);
    }

    #[test]
    fn test_accessor_round_trip() {
        let mut set: Cset<i32> = Cset::new();
        set.set_seed(12345);
        assert_eq!(set.get_seed(), 12345);
        set.set_max_load_factor(0.9);
        assert_eq!(set.get_max_load_factor(), 0.9);
        set.set_min_load_factor(0.1);
        assert_eq!(set.get_min_load_factor(), 0.1);
        set.set_size(3);
        assert_eq!(set.get_size(), 3);
    }

    // --- M4: add / contains / resize ----------------------------------------
    #[test]
    fn test_add_duplicate_noop() {
        let mut set: Cset<i32> = Cset::new();
        set.add(1);
        set.add(2);
        assert_eq!(set.size(), 2);
        set.add(2);
        assert_eq!(set.size(), 2);
    }

    #[test]
    fn test_contains_true_false() {
        let mut set: Cset<i32> = Cset::new();
        set.add(34);
        set.add(25);
        set.add(56);
        assert!(set.contains(&34));
        assert!(!set.contains(&100));
    }

    #[test]
    fn test_resize_on_load_factor() {
        // add enough elements to force capacity doubling; assert capacity() grows
        let mut set: Cset<i32> = Cset::new();
        let initial_cap = set.capacity();
        for i in 0..20 {
            set.add(i);
        }
        assert!(set.capacity() > initial_cap);
        assert_eq!(set.size(), 20);
        for i in 0..20 {
            assert!(set.contains(&i));
        }
    }

    // --- M5: remove / tombstones / clear ------------------------------------
    #[test]
    fn test_remove_then_size_zero() {
        // mirrors README cset__remove example -- add(34); remove(34); size()==0
        let mut set: Cset<i32> = Cset::new();
        set.add(34);
        assert_eq!(set.size(), 1);
        set.remove(34);
        assert_eq!(set.size(), 0);
        assert!(!set.contains(&34));
    }

    #[test]
    fn test_remove_missing_is_noop() {
        // removing an absent value leaves size() unchanged
        let mut set: Cset<i32> = Cset::new();
        set.add(1);
        set.add(2);
        assert_eq!(set.size(), 2);
        set.remove(999);
        assert_eq!(set.size(), 2);
    }

    #[test]
    fn test_clear_resets_size() {
        // mirrors README cset__clear example -- clear() -> size()==0
        let mut set: Cset<i32> = Cset::new();
        set.add(1);
        set.add(2);
        set.add(3);
        set.clear();
        assert_eq!(set.size(), 0);
        assert_eq!(set.capacity(), CSET_INITIAL_CAP as i32);
        assert!(!set.contains(&1));
    }

    // --- M6/M7: custom comparator dispatch ----------------------------------
    #[test]
    fn test_custom_comparator_dedup_by_field() {
        // mirrors README Node example -- set_comparator(node_comparator) dedupes by x
        let mut set: Cset<Node> = Cset::new();
        set.set_comparator(node_comparator);
        set.add(Node { x: 1, y: 2 });
        assert_eq!(set.size(), 1);
        set.add(Node { x: 1, y: 999 });
        assert_eq!(set.size(), 1);
        set.add(Node { x: 2, y: 2 });
        assert_eq!(set.size(), 2);
    }

    // --- M6: iteration -------------------------------------------------------
    #[test]
    fn test_iterator_yields_all_elements() {
        // iter() returns exactly the live elements, compared as a multiset (bucket order)
        let mut set: Cset<i32> = Cset::new();
        set.add(1);
        set.add(2);
        set.add(3);
        let mut values = set.iter();
        values.sort();
        assert_eq!(values, vec![1, 2, 3]);
    }

    // --- M8: set algebra ------------------------------------------------------
    #[test]
    fn test_intersect_sizes() {
        // mirrors README cset__intersect example -- intersect of [12,13,14] and [12,13,16] => size 2
        let mut a: Cset<i32> = Cset::new();
        a.add(12);
        a.add(13);
        a.add(14);
        let mut b: Cset<i32> = Cset::new();
        b.add(12);
        b.add(13);
        b.add(16);
        let mut result: Cset<i32> = Cset::new();
        result.intersect(&a, &b);
        assert_eq!(result.size(), 2);
        assert!(result.contains(&12));
        assert!(result.contains(&13));
        assert!(!result.contains(&14));
    }

    #[test]
    fn test_union_sizes() {
        // mirrors README cset__union example -- sizes 5 then 6 after adding to b
        let mut a: Cset<i32> = Cset::new();
        a.add(1);
        a.add(2);
        a.add(3);
        let mut b: Cset<i32> = Cset::new();
        b.add(3);
        b.add(4);
        let mut result: Cset<i32> = Cset::new();
        result.union(&a, &b);
        assert_eq!(result.size(), 4);
        b.add(5);
        let mut result2: Cset<i32> = Cset::new();
        result2.union(&a, &b);
        assert_eq!(result2.size(), 5);
    }

    #[test]
    fn test_is_disjoint() {
        // is_disjoint() true for non-overlapping sets, false once they share an element
        let mut a: Cset<i32> = Cset::new();
        a.add(1);
        a.add(2);
        let mut b: Cset<i32> = Cset::new();
        b.add(3);
        b.add(4);
        assert!(a.is_disjoint(&b));
        b.add(1);
        assert!(!a.is_disjoint(&b));
    }

    #[test]
    fn test_difference() {
        // difference(result, a, b) contains only a's elements absent from b
        let mut a: Cset<i32> = Cset::new();
        a.add(1);
        a.add(2);
        a.add(3);
        let mut b: Cset<i32> = Cset::new();
        b.add(2);
        b.add(3);
        let mut result: Cset<i32> = Cset::new();
        result.difference(&a, &b);
        assert_eq!(result.size(), 1);
        assert!(result.contains(&1));
        assert!(!result.contains(&2));
        assert!(!result.contains(&3));
    }
}