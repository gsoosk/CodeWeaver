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
pub type ArrayListValue = *mut ::core::ffi::c_void;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _ArrayList {
    pub data: *mut ArrayListValue,
    pub length: ::core::ffi::c_uint,
    pub _alloced: ::core::ffi::c_uint,
}
pub type ArrayList = _ArrayList;
pub type ArrayListEqualFunc =
    Option<unsafe extern "C" fn(ArrayListValue, ArrayListValue) -> ::core::ffi::c_int>;
pub type ArrayListCompareFunc =
    Option<unsafe extern "C" fn(ArrayListValue, ArrayListValue) -> ::core::ffi::c_int>;
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
#[no_mangle]
pub unsafe extern "C" fn arraylist_new(mut length: ::core::ffi::c_uint) -> *mut ArrayList {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_free(mut arraylist: *mut ArrayList) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn arraylist_enlarge(mut arraylist: *mut ArrayList) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_insert(
    mut arraylist: *mut ArrayList,
    mut index: ::core::ffi::c_uint,
    mut data: ArrayListValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_append(
    mut arraylist: *mut ArrayList,
    mut data: ArrayListValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_prepend(
    mut arraylist: *mut ArrayList,
    mut data: ArrayListValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_remove_range(
    mut arraylist: *mut ArrayList,
    mut index: ::core::ffi::c_uint,
    mut length: ::core::ffi::c_uint,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_remove(
    mut arraylist: *mut ArrayList,
    mut index: ::core::ffi::c_uint,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_index_of(
    mut arraylist: *mut ArrayList,
    mut callback: ArrayListEqualFunc,
    mut data: ArrayListValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_clear(mut arraylist: *mut ArrayList) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn arraylist_sort_internal(
    mut list_data: *mut ArrayListValue,
    mut list_length: ::core::ffi::c_uint,
    mut compare_func: ArrayListCompareFunc,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn arraylist_sort(
    mut arraylist: *mut ArrayList,
    mut compare_func: ArrayListCompareFunc,
) {
    unimplemented!("CodeWeaver must implement this function")
}
