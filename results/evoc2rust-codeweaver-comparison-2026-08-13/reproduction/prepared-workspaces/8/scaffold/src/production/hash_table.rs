extern "C" {
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_calloc(nmemb: size_t, bytes: size_t) -> *mut ::core::ffi::c_void;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _HashTable {
    pub table: *mut *mut HashTableEntry,
    pub table_size: ::core::ffi::c_uint,
    pub hash_func: HashTableHashFunc,
    pub equal_func: HashTableEqualFunc,
    pub key_free_func: HashTableKeyFreeFunc,
    pub value_free_func: HashTableValueFreeFunc,
    pub entries: ::core::ffi::c_uint,
    pub prime_index: ::core::ffi::c_uint,
}
pub type HashTableValueFreeFunc = Option<unsafe extern "C" fn(HashTableValue) -> ()>;
pub type HashTableValue = *mut ::core::ffi::c_void;
pub type HashTableKeyFreeFunc = Option<unsafe extern "C" fn(HashTableKey) -> ()>;
pub type HashTableKey = *mut ::core::ffi::c_void;
pub type HashTableEqualFunc =
    Option<unsafe extern "C" fn(HashTableKey, HashTableKey) -> ::core::ffi::c_int>;
pub type HashTableHashFunc = Option<unsafe extern "C" fn(HashTableKey) -> ::core::ffi::c_uint>;
pub type HashTableEntry = _HashTableEntry;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _HashTableEntry {
    pub pair: HashTablePair,
    pub next: *mut HashTableEntry,
}
pub type HashTablePair = _HashTablePair;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _HashTablePair {
    pub key: HashTableKey,
    pub value: HashTableValue,
}
pub type HashTable = _HashTable;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _HashTableIterator {
    pub hash_table: *mut HashTable,
    pub next_entry: *mut HashTableEntry,
    pub next_chain: ::core::ffi::c_uint,
}
pub type HashTableIterator = _HashTableIterator;
#[inline]
unsafe extern "C" fn __bswap_16(mut __bsx: __uint16_t) -> __uint16_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __bswap_32(mut __bsx: __uint32_t) -> __uint32_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __bswap_64(mut __bsx: __uint64_t) -> __uint64_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __uint16_identity(mut __x: __uint16_t) -> __uint16_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __uint32_identity(mut __x: __uint32_t) -> __uint32_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __uint64_identity(mut __x: __uint64_t) -> __uint64_t {
    unimplemented!("CodeWeaver must implement this function")
}
pub const NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
pub const HASH_TABLE_NULL: *mut ::core::ffi::c_void =
    ::core::ptr::null_mut::<::core::ffi::c_void>();
static mut hash_table_primes: [::core::ffi::c_uint; 24] = [
    193 as ::core::ffi::c_int as ::core::ffi::c_uint,
    389 as ::core::ffi::c_int as ::core::ffi::c_uint,
    769 as ::core::ffi::c_int as ::core::ffi::c_uint,
    1543 as ::core::ffi::c_int as ::core::ffi::c_uint,
    3079 as ::core::ffi::c_int as ::core::ffi::c_uint,
    6151 as ::core::ffi::c_int as ::core::ffi::c_uint,
    12289 as ::core::ffi::c_int as ::core::ffi::c_uint,
    24593 as ::core::ffi::c_int as ::core::ffi::c_uint,
    49157 as ::core::ffi::c_int as ::core::ffi::c_uint,
    98317 as ::core::ffi::c_int as ::core::ffi::c_uint,
    196613 as ::core::ffi::c_int as ::core::ffi::c_uint,
    393241 as ::core::ffi::c_int as ::core::ffi::c_uint,
    786433 as ::core::ffi::c_int as ::core::ffi::c_uint,
    1572869 as ::core::ffi::c_int as ::core::ffi::c_uint,
    3145739 as ::core::ffi::c_int as ::core::ffi::c_uint,
    6291469 as ::core::ffi::c_int as ::core::ffi::c_uint,
    12582917 as ::core::ffi::c_int as ::core::ffi::c_uint,
    25165843 as ::core::ffi::c_int as ::core::ffi::c_uint,
    50331653 as ::core::ffi::c_int as ::core::ffi::c_uint,
    100663319 as ::core::ffi::c_int as ::core::ffi::c_uint,
    201326611 as ::core::ffi::c_int as ::core::ffi::c_uint,
    402653189 as ::core::ffi::c_int as ::core::ffi::c_uint,
    805306457 as ::core::ffi::c_int as ::core::ffi::c_uint,
    1610612741 as ::core::ffi::c_int as ::core::ffi::c_uint,
];
static mut hash_table_num_primes: ::core::ffi::c_uint = 0;
unsafe extern "C" fn hash_table_allocate_table(
    mut hash_table: *mut HashTable,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn hash_table_free_entry(
    mut hash_table: *mut HashTable,
    mut entry: *mut HashTableEntry,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_new(
    mut hash_func: HashTableHashFunc,
    mut equal_func: HashTableEqualFunc,
) -> *mut HashTable {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_free(mut hash_table: *mut HashTable) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_register_free_functions(
    mut hash_table: *mut HashTable,
    mut key_free_func: HashTableKeyFreeFunc,
    mut value_free_func: HashTableValueFreeFunc,
) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn hash_table_enlarge(mut hash_table: *mut HashTable) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_insert(
    mut hash_table: *mut HashTable,
    mut key: HashTableKey,
    mut value: HashTableValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_lookup(
    mut hash_table: *mut HashTable,
    mut key: HashTableKey,
) -> HashTableValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_remove(
    mut hash_table: *mut HashTable,
    mut key: HashTableKey,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_num_entries(
    mut hash_table: *mut HashTable,
) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_iterate(
    mut hash_table: *mut HashTable,
    mut iterator: *mut HashTableIterator,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_iter_has_more(
    mut iterator: *mut HashTableIterator,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn hash_table_iter_next(
    mut iterator: *mut HashTableIterator,
) -> HashTablePair {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn run_static_initializers() {
    unimplemented!("CodeWeaver must implement this function")
}
#[used]
#[cfg_attr(target_os = "linux", link_section = ".init_array")]
#[cfg_attr(target_os = "windows", link_section = ".CRT$XIB")]
#[cfg_attr(target_os = "macos", link_section = "__DATA,__mod_init_func")]
static INIT_ARRAY: [unsafe extern "C" fn(); 1] = [run_static_initializers];
