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
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _BloomFilter {
    pub hash_func: BloomFilterHashFunc,
    pub table: *mut ::core::ffi::c_uchar,
    pub table_size: ::core::ffi::c_uint,
    pub num_functions: ::core::ffi::c_uint,
}
pub type BloomFilterHashFunc =
    Option<unsafe extern "C" fn(BloomFilterValue) -> ::core::ffi::c_uint>;
pub type BloomFilterValue = *mut ::core::ffi::c_void;
pub type BloomFilter = _BloomFilter;
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
static mut salts: [::core::ffi::c_uint; 64] = [
    0x1953c322 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x588ccf17 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x64bf600c as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xa6be3f3d as ::core::ffi::c_uint,
    0x341a02ea as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x15b03217 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x3b062858 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x5956fd06 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x18b5624f as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xe3be0b46 as ::core::ffi::c_uint,
    0x20ffcd5c as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xa35dfd2b as ::core::ffi::c_uint,
    0x1fc4a9bf as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x57c45d5c as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xa8661c4a as ::core::ffi::c_uint,
    0x4f1b74d2 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x5a6dde13 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x3b18dac6 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x5a8afbf as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xbbda2fe2 as ::core::ffi::c_uint,
    0xa2520d78 as ::core::ffi::c_uint,
    0xe7934849 as ::core::ffi::c_uint,
    0xd541bc75 as ::core::ffi::c_uint,
    0x9a55b57 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x9b345ae2 as ::core::ffi::c_uint,
    0xfc2d26af as ::core::ffi::c_uint,
    0x38679cef as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x81bd1e0d as ::core::ffi::c_uint,
    0x654681ae as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x4b3d87ad as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xd5ff10fb as ::core::ffi::c_uint,
    0x23b32f67 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xafc7e366 as ::core::ffi::c_uint,
    0xdd955ead as ::core::ffi::c_uint,
    0xe7c34b1c as ::core::ffi::c_uint,
    0xfeace0a6 as ::core::ffi::c_uint,
    0xeb16f09d as ::core::ffi::c_uint,
    0x3c57a72d as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x2c8294c5 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xba92662a as ::core::ffi::c_uint,
    0xcd5b2d14 as ::core::ffi::c_uint,
    0x743936c8 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x2489beff as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xc6c56e00 as ::core::ffi::c_uint,
    0x74a4f606 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xb244a94a as ::core::ffi::c_uint,
    0x5edfc423 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xf1901934 as ::core::ffi::c_uint,
    0x24af7691 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xf6c98b25 as ::core::ffi::c_uint,
    0xea25af46 as ::core::ffi::c_uint,
    0x76d5f2e6 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x5e33cdf2 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x445eb357 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x88556bd2 as ::core::ffi::c_uint,
    0x70d1da7a as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x54449368 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x381020bc as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x1c0520bf as ::core::ffi::c_int as ::core::ffi::c_uint,
    0xf7e44942 as ::core::ffi::c_uint,
    0xa27e2a58 as ::core::ffi::c_uint,
    0x66866fc5 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x12519ce7 as ::core::ffi::c_int as ::core::ffi::c_uint,
    0x437a8456 as ::core::ffi::c_int as ::core::ffi::c_uint,
];
#[no_mangle]
pub unsafe extern "C" fn bloom_filter_new(
    mut table_size: ::core::ffi::c_uint,
    mut hash_func: BloomFilterHashFunc,
    mut num_functions: ::core::ffi::c_uint,
) -> *mut BloomFilter {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn bloom_filter_free(mut bloomfilter: *mut BloomFilter) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn bloom_filter_insert(
    mut bloomfilter: *mut BloomFilter,
    mut value: BloomFilterValue,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn bloom_filter_query(
    mut bloomfilter: *mut BloomFilter,
    mut value: BloomFilterValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn bloom_filter_read(
    mut bloomfilter: *mut BloomFilter,
    mut array: *mut ::core::ffi::c_uchar,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn bloom_filter_load(
    mut bloomfilter: *mut BloomFilter,
    mut array: *mut ::core::ffi::c_uchar,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn bloom_filter_union(
    mut filter1: *mut BloomFilter,
    mut filter2: *mut BloomFilter,
) -> *mut BloomFilter {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn bloom_filter_intersection(
    mut filter1: *mut BloomFilter,
    mut filter2: *mut BloomFilter,
) -> *mut BloomFilter {
    unimplemented!("CodeWeaver must implement this function")
}
