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
pub struct _Set {
    pub table: *mut *mut SetEntry,
    pub entries: ::core::ffi::c_uint,
    pub table_size: ::core::ffi::c_uint,
    pub prime_index: ::core::ffi::c_uint,
    pub hash_func: SetHashFunc,
    pub equal_func: SetEqualFunc,
    pub free_func: SetFreeFunc,
}
pub type SetFreeFunc = Option<unsafe extern "C" fn(SetValue) -> ()>;
pub type SetValue = *mut ::core::ffi::c_void;
pub type SetEqualFunc = Option<unsafe extern "C" fn(SetValue, SetValue) -> ::core::ffi::c_int>;
pub type SetHashFunc = Option<unsafe extern "C" fn(SetValue) -> ::core::ffi::c_uint>;
pub type SetEntry = _SetEntry;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _SetEntry {
    pub data: SetValue,
    pub next: *mut SetEntry,
}
pub type Set = _Set;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _SetIterator {
    pub set: *mut Set,
    pub next_entry: *mut SetEntry,
    pub next_chain: ::core::ffi::c_uint,
}
pub type SetIterator = _SetIterator;
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
pub const SET_NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
static mut set_primes: [::core::ffi::c_uint; 24] = [
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
static mut set_num_primes: ::core::ffi::c_uint = 0;
unsafe extern "C" fn set_allocate_table(mut set: *mut Set) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn set_free_entry(mut set: *mut Set, mut entry: *mut SetEntry) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_new(
    mut hash_func: SetHashFunc,
    mut equal_func: SetEqualFunc,
) -> *mut Set {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_free(mut set: *mut Set) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_register_free_function(mut set: *mut Set, mut free_func: SetFreeFunc) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn set_enlarge(mut set: *mut Set) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_insert(mut set: *mut Set, mut data: SetValue) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_remove(mut set: *mut Set, mut data: SetValue) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_query(mut set: *mut Set, mut data: SetValue) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_num_entries(mut set: *mut Set) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_to_array(mut set: *mut Set) -> *mut SetValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_union(mut set1: *mut Set, mut set2: *mut Set) -> *mut Set {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_intersection(mut set1: *mut Set, mut set2: *mut Set) -> *mut Set {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_iterate(mut set: *mut Set, mut iter: *mut SetIterator) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_iter_next(mut iterator: *mut SetIterator) -> SetValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn set_iter_has_more(mut iterator: *mut SetIterator) -> ::core::ffi::c_int {
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
