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
pub struct _SListEntry {
    pub data: SListValue,
    pub next: *mut SListEntry,
}
pub type SListEntry = _SListEntry;
pub type SListValue = *mut ::core::ffi::c_void;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _SListIterator {
    pub prev_next: *mut *mut SListEntry,
    pub current: *mut SListEntry,
}
pub type SListIterator = _SListIterator;
pub type SListCompareFunc =
    Option<unsafe extern "C" fn(SListValue, SListValue) -> ::core::ffi::c_int>;
pub type SListEqualFunc =
    Option<unsafe extern "C" fn(SListValue, SListValue) -> ::core::ffi::c_int>;
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
pub const SLIST_NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
#[no_mangle]
pub unsafe extern "C" fn slist_free(mut list: *mut SListEntry) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_prepend(
    mut list: *mut *mut SListEntry,
    mut data: SListValue,
) -> *mut SListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_append(
    mut list: *mut *mut SListEntry,
    mut data: SListValue,
) -> *mut SListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_data(mut listentry: *mut SListEntry) -> SListValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_set_data(mut listentry: *mut SListEntry, mut data: SListValue) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_next(mut listentry: *mut SListEntry) -> *mut SListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_nth_entry(
    mut list: *mut SListEntry,
    mut n: ::core::ffi::c_uint,
) -> *mut SListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_nth_data(
    mut list: *mut SListEntry,
    mut n: ::core::ffi::c_uint,
) -> SListValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_length(mut list: *mut SListEntry) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_to_array(mut list: *mut SListEntry) -> *mut SListValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_remove_entry(
    mut list: *mut *mut SListEntry,
    mut entry: *mut SListEntry,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_remove_data(
    mut list: *mut *mut SListEntry,
    mut callback: SListEqualFunc,
    mut data: SListValue,
) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn slist_sort_internal(
    mut list: *mut *mut SListEntry,
    mut compare_func: SListCompareFunc,
) -> *mut SListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_sort(
    mut list: *mut *mut SListEntry,
    mut compare_func: SListCompareFunc,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_find_data(
    mut list: *mut SListEntry,
    mut callback: SListEqualFunc,
    mut data: SListValue,
) -> *mut SListEntry {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_iterate(
    mut list: *mut *mut SListEntry,
    mut iter: *mut SListIterator,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_iter_has_more(mut iter: *mut SListIterator) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_iter_next(mut iter: *mut SListIterator) -> SListValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn slist_iter_remove(mut iter: *mut SListIterator) {
    unimplemented!("CodeWeaver must implement this function")
}
