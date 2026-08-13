extern "C" {
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_realloc(ptr: *mut ::core::ffi::c_void, bytes: size_t)
        -> *mut ::core::ffi::c_void;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type BinaryHeapType = ::core::ffi::c_uint;
pub const BINARY_HEAP_TYPE_MAX: BinaryHeapType = 1;
pub const BINARY_HEAP_TYPE_MIN: BinaryHeapType = 0;
pub type BinaryHeapValue = *mut ::core::ffi::c_void;
pub type BinaryHeapCompareFunc =
    Option<unsafe extern "C" fn(BinaryHeapValue, BinaryHeapValue) -> ::core::ffi::c_int>;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _BinaryHeap {
    pub heap_type: BinaryHeapType,
    pub values: *mut BinaryHeapValue,
    pub num_values: ::core::ffi::c_uint,
    pub alloced_size: ::core::ffi::c_uint,
    pub compare_func: BinaryHeapCompareFunc,
}
pub type BinaryHeap = _BinaryHeap;
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
pub const BINARY_HEAP_NULL: *mut ::core::ffi::c_void =
    ::core::ptr::null_mut::<::core::ffi::c_void>();
unsafe extern "C" fn binary_heap_cmp(
    mut heap: *mut BinaryHeap,
    mut data1: BinaryHeapValue,
    mut data2: BinaryHeapValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binary_heap_new(
    mut heap_type: BinaryHeapType,
    mut compare_func: BinaryHeapCompareFunc,
) -> *mut BinaryHeap {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binary_heap_free(mut heap: *mut BinaryHeap) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binary_heap_insert(
    mut heap: *mut BinaryHeap,
    mut value: BinaryHeapValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binary_heap_pop(mut heap: *mut BinaryHeap) -> BinaryHeapValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binary_heap_num_entries(mut heap: *mut BinaryHeap) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
