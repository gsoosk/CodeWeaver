extern "C" {
    fn memmove(
        __dest: *mut ::core::ffi::c_void,
        __src: *const ::core::ffi::c_void,
        __n: size_t,
    ) -> *mut ::core::ffi::c_void;
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_realloc(ptr: *mut ::core::ffi::c_void, bytes: size_t)
        -> *mut ::core::ffi::c_void;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type SortedArrayValue = *mut ::core::ffi::c_void;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _SortedArray {
    pub data: *mut SortedArrayValue,
    pub length: ::core::ffi::c_uint,
    pub _alloced: ::core::ffi::c_uint,
    pub equ_func: SortedArrayEqualFunc,
    pub cmp_func: SortedArrayCompareFunc,
}
pub type SortedArrayCompareFunc =
    Option<unsafe extern "C" fn(SortedArrayValue, SortedArrayValue) -> ::core::ffi::c_int>;
pub type SortedArrayEqualFunc =
    Option<unsafe extern "C" fn(SortedArrayValue, SortedArrayValue) -> ::core::ffi::c_int>;
pub type SortedArray = _SortedArray;
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
unsafe extern "C" fn sortedarray_first_index(
    mut sortedarray: *mut SortedArray,
    mut data: SortedArrayValue,
    mut left: ::core::ffi::c_uint,
    mut right: ::core::ffi::c_uint,
) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn sortedarray_last_index(
    mut sortedarray: *mut SortedArray,
    mut data: SortedArrayValue,
    mut left: ::core::ffi::c_uint,
    mut right: ::core::ffi::c_uint,
) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_get(
    mut array: *mut SortedArray,
    mut i: ::core::ffi::c_uint,
) -> *mut SortedArrayValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_length(mut array: *mut SortedArray) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_new(
    mut length: ::core::ffi::c_uint,
    mut equ_func: SortedArrayEqualFunc,
    mut cmp_func: SortedArrayCompareFunc,
) -> *mut SortedArray {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_free(mut sortedarray: *mut SortedArray) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_remove(
    mut sortedarray: *mut SortedArray,
    mut index: ::core::ffi::c_uint,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_remove_range(
    mut sortedarray: *mut SortedArray,
    mut index: ::core::ffi::c_uint,
    mut length: ::core::ffi::c_uint,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_insert(
    mut sortedarray: *mut SortedArray,
    mut data: SortedArrayValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_index_of(
    mut sortedarray: *mut SortedArray,
    mut data: SortedArrayValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn sortedarray_clear(mut sortedarray: *mut SortedArray) {
    unimplemented!("CodeWeaver must implement this function")
}
