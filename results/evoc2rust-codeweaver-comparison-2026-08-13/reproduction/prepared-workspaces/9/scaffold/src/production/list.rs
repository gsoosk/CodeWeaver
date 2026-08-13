extern "C" {
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _ListEntry {
    pub data: ListValue,
    pub prev: *mut ListEntry,
    pub next: *mut ListEntry,
}
pub type ListEntry = _ListEntry;
pub type ListValue = *mut ::core::ffi::c_void;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _ListIterator {
    pub prev_next: *mut *mut ListEntry,
    pub current: *mut ListEntry,
}
pub type ListIterator = _ListIterator;
pub type ListCompareFunc = Option<unsafe extern "C" fn(ListValue, ListValue) -> ::core::ffi::c_int>;
pub type ListEqualFunc = Option<unsafe extern "C" fn(ListValue, ListValue) -> ::core::ffi::c_int>;
pub const NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
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
pub const LIST_NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
#[no_mangle]
pub unsafe extern "C" fn list_free(mut list: *mut ListEntry) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_prepend(
    mut list: *mut *mut ListEntry,
    mut data: ListValue,
) -> *mut ListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_append(
    mut list: *mut *mut ListEntry,
    mut data: ListValue,
) -> *mut ListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_data(mut listentry: *mut ListEntry) -> ListValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_set_data(mut listentry: *mut ListEntry, mut value: ListValue) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_prev(mut listentry: *mut ListEntry) -> *mut ListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_next(mut listentry: *mut ListEntry) -> *mut ListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_nth_entry(
    mut list: *mut ListEntry,
    mut n: ::core::ffi::c_uint,
) -> *mut ListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_nth_data(
    mut list: *mut ListEntry,
    mut n: ::core::ffi::c_uint,
) -> ListValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_length(mut list: *mut ListEntry) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_to_array(mut list: *mut ListEntry) -> *mut ListValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_remove_entry(
    mut list: *mut *mut ListEntry,
    mut entry: *mut ListEntry,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_remove_data(
    mut list: *mut *mut ListEntry,
    mut callback: ListEqualFunc,
    mut data: ListValue,
) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn list_sort_internal(
    mut list: *mut *mut ListEntry,
    mut compare_func: ListCompareFunc,
) -> *mut ListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_sort(
    mut list: *mut *mut ListEntry,
    mut compare_func: ListCompareFunc,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_find_data(
    mut list: *mut ListEntry,
    mut callback: ListEqualFunc,
    mut data: ListValue,
) -> *mut ListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_iterate(mut list: *mut *mut ListEntry, mut iter: *mut ListIterator) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_iter_has_more(mut iter: *mut ListIterator) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_iter_next(mut iter: *mut ListIterator) -> ListValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn list_iter_remove(mut iter: *mut ListIterator) {
    unimplemented!("CodeWeaver must implement this function")
}
