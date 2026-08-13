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
pub struct _Trie {
    pub root_node: *mut TrieNode,
}
pub type TrieNode = _TrieNode;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _TrieNode {
    pub data: TrieValue,
    pub use_count: ::core::ffi::c_uint,
    pub next: [*mut TrieNode; 256],
}
pub type TrieValue = *mut ::core::ffi::c_void;
pub type Trie = _Trie;
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
pub const TRIE_NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
#[no_mangle]
pub unsafe extern "C" fn trie_new() -> *mut Trie {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn trie_free_list_push(mut list: *mut *mut TrieNode, mut node: *mut TrieNode) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn trie_free_list_pop(mut list: *mut *mut TrieNode) -> *mut TrieNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn trie_free(mut trie: *mut Trie) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn trie_find_end(
    mut trie: *mut Trie,
    mut key: *mut ::core::ffi::c_char,
) -> *mut TrieNode {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn trie_find_end_binary(
    mut trie: *mut Trie,
    mut key: *mut ::core::ffi::c_uchar,
    mut key_length: ::core::ffi::c_int,
) -> *mut TrieNode {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn trie_insert_rollback(mut trie: *mut Trie, mut key: *mut ::core::ffi::c_uchar) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn trie_insert(
    mut trie: *mut Trie,
    mut key: *mut ::core::ffi::c_char,
    mut value: TrieValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn trie_insert_binary(
    mut trie: *mut Trie,
    mut key: *mut ::core::ffi::c_uchar,
    mut key_length: ::core::ffi::c_int,
    mut value: TrieValue,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn trie_remove_binary(
    mut trie: *mut Trie,
    mut key: *mut ::core::ffi::c_uchar,
    mut key_length: ::core::ffi::c_int,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn trie_remove(
    mut trie: *mut Trie,
    mut key: *mut ::core::ffi::c_char,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn trie_lookup(
    mut trie: *mut Trie,
    mut key: *mut ::core::ffi::c_char,
) -> TrieValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn trie_lookup_binary(
    mut trie: *mut Trie,
    mut key: *mut ::core::ffi::c_uchar,
    mut key_length: ::core::ffi::c_int,
) -> TrieValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn trie_num_entries(mut trie: *mut Trie) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
