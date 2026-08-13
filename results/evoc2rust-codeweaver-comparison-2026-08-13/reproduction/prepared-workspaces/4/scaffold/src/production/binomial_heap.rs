extern "C" {
    fn memcpy(
        __dest: *mut ::core::ffi::c_void,
        __src: *const ::core::ffi::c_void,
        __n: size_t,
    ) -> *mut ::core::ffi::c_void;
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_calloc(nmemb: size_t, bytes: size_t) -> *mut ::core::ffi::c_void;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type BinomialHeapType = ::core::ffi::c_uint;
pub const BINOMIAL_HEAP_TYPE_MAX: BinomialHeapType = 1;
pub const BINOMIAL_HEAP_TYPE_MIN: BinomialHeapType = 0;
pub type BinomialHeapValue = *mut ::core::ffi::c_void;
pub type BinomialHeapCompareFunc =
    Option<unsafe extern "C" fn(BinomialHeapValue, BinomialHeapValue) -> ::core::ffi::c_int>;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _BinomialHeap {
    pub heap_type: BinomialHeapType,
    pub compare_func: BinomialHeapCompareFunc,
    pub num_values: ::core::ffi::c_uint,
    pub roots: *mut *mut BinomialTree,
    pub roots_length: ::core::ffi::c_uint,
}
pub type BinomialTree = _BinomialTree;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _BinomialTree {
    pub value: BinomialHeapValue,
    pub order: ::core::ffi::c_ushort,
    pub refcount: ::core::ffi::c_ushort,
    pub subtrees: *mut *mut BinomialTree,
}
pub type BinomialHeap = _BinomialHeap;
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
pub const UINT_MAX: ::core::ffi::c_uint = (__INT_MAX__ as ::core::ffi::c_uint)
    .wrapping_mul(2 as ::core::ffi::c_uint)
    .wrapping_add(1 as ::core::ffi::c_uint);
pub const BINOMIAL_HEAP_NULL: *mut ::core::ffi::c_void =
    ::core::ptr::null_mut::<::core::ffi::c_void>();
unsafe extern "C" fn binomial_heap_cmp(
    mut heap: *mut BinomialHeap,
    mut data1: BinomialHeapValue,
    mut data2: BinomialHeapValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn binomial_tree_ref(mut tree: *mut BinomialTree) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn binomial_tree_unref(mut tree: *mut BinomialTree) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn binomial_tree_merge(
    mut heap: *mut BinomialHeap,
    mut tree1: *mut BinomialTree,
    mut tree2: *mut BinomialTree,
) -> *mut BinomialTree {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn binomial_heap_merge_undo(
    mut new_roots: *mut *mut BinomialTree,
    mut count: ::core::ffi::c_uint,
) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn binomial_heap_merge(
    mut heap: *mut BinomialHeap,
    mut other: *mut BinomialHeap,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binomial_heap_new(
    mut heap_type: BinomialHeapType,
    mut compare_func: BinomialHeapCompareFunc,
) -> *mut BinomialHeap {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binomial_heap_free(mut heap: *mut BinomialHeap) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binomial_heap_insert(
    mut heap: *mut BinomialHeap,
    mut value: BinomialHeapValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binomial_heap_pop(mut heap: *mut BinomialHeap) -> BinomialHeapValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn binomial_heap_num_entries(
    mut heap: *mut BinomialHeap,
) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
pub const __INT_MAX__: ::core::ffi::c_int = 2147483647 as ::core::ffi::c_int;
