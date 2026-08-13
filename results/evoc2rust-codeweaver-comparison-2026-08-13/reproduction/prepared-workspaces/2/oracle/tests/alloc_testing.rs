extern "C" {
    fn malloc(__size: size_t) -> *mut ::core::ffi::c_void;
    fn free(__ptr: *mut ::core::ffi::c_void);
    fn memcpy(
        __dest: *mut ::core::ffi::c_void,
        __src: *const ::core::ffi::c_void,
        __n: size_t,
    ) -> *mut ::core::ffi::c_void;
    fn memset(
        __s: *mut ::core::ffi::c_void,
        __c: ::core::ffi::c_int,
        __n: size_t,
    ) -> *mut ::core::ffi::c_void;
    fn strcpy(
        __dest: *mut ::core::ffi::c_char,
        __src: *const ::core::ffi::c_char,
    ) -> *mut ::core::ffi::c_char;
    fn strlen(__s: *const ::core::ffi::c_char) -> size_t;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type BlockHeader = _BlockHeader;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _BlockHeader {
    pub magic_number: ::core::ffi::c_uint,
    pub bytes: size_t,
}
#[inline]
unsafe extern "C" fn __bswap_16(mut __bsx: __uint16_t) -> __uint16_t {
    return (__bsx as ::core::ffi::c_int >> 8 as ::core::ffi::c_int & 0xff as ::core::ffi::c_int
        | (__bsx as ::core::ffi::c_int & 0xff as ::core::ffi::c_int) << 8 as ::core::ffi::c_int)
        as __uint16_t;
}
#[inline]
unsafe extern "C" fn __bswap_32(mut __bsx: __uint32_t) -> __uint32_t {
    return (__bsx & 0xff000000 as __uint32_t) >> 24 as ::core::ffi::c_int
        | (__bsx & 0xff0000 as __uint32_t) >> 8 as ::core::ffi::c_int
        | (__bsx & 0xff00 as __uint32_t) << 8 as ::core::ffi::c_int
        | (__bsx & 0xff as __uint32_t) << 24 as ::core::ffi::c_int;
}
#[inline]
unsafe extern "C" fn __bswap_64(mut __bsx: __uint64_t) -> __uint64_t {
    return ((__bsx as ::core::ffi::c_ulonglong & 0xff00000000000000 as ::core::ffi::c_ulonglong)
        >> 56 as ::core::ffi::c_int
        | (__bsx as ::core::ffi::c_ulonglong & 0xff000000000000 as ::core::ffi::c_ulonglong)
            >> 40 as ::core::ffi::c_int
        | (__bsx as ::core::ffi::c_ulonglong & 0xff0000000000 as ::core::ffi::c_ulonglong)
            >> 24 as ::core::ffi::c_int
        | (__bsx as ::core::ffi::c_ulonglong & 0xff00000000 as ::core::ffi::c_ulonglong)
            >> 8 as ::core::ffi::c_int
        | (__bsx as ::core::ffi::c_ulonglong & 0xff000000 as ::core::ffi::c_ulonglong)
            << 8 as ::core::ffi::c_int
        | (__bsx as ::core::ffi::c_ulonglong & 0xff0000 as ::core::ffi::c_ulonglong)
            << 24 as ::core::ffi::c_int
        | (__bsx as ::core::ffi::c_ulonglong & 0xff00 as ::core::ffi::c_ulonglong)
            << 40 as ::core::ffi::c_int
        | (__bsx as ::core::ffi::c_ulonglong & 0xff as ::core::ffi::c_ulonglong)
            << 56 as ::core::ffi::c_int) as __uint64_t;
}
#[inline]
unsafe extern "C" fn __uint16_identity(mut __x: __uint16_t) -> __uint16_t {
    return __x;
}
#[inline]
unsafe extern "C" fn __uint32_identity(mut __x: __uint32_t) -> __uint32_t {
    return __x;
}
#[inline]
unsafe extern "C" fn __uint64_identity(mut __x: __uint64_t) -> __uint64_t {
    return __x;
}
pub const NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
pub const ALLOC_TEST_MAGIC: ::core::ffi::c_int = 0x72ec82d2 as ::core::ffi::c_int;
pub const MALLOC_PATTERN: ::core::ffi::c_uint = 0xbaadf00d as ::core::ffi::c_uint;
pub const FREE_PATTERN: ::core::ffi::c_uint = 0xdeadbeef as ::core::ffi::c_uint;
static mut allocated_bytes: size_t = 0 as size_t;
#[no_mangle]
pub static mut allocation_limit: ::core::ffi::c_int = -(1 as ::core::ffi::c_int);
unsafe extern "C" fn alloc_test_get_header(mut ptr: *mut ::core::ffi::c_void) -> *mut BlockHeader {
    let mut result: *mut BlockHeader = ::core::ptr::null_mut::<BlockHeader>();
    result = (ptr as *mut BlockHeader).offset(-(1 as ::core::ffi::c_int as isize));
    '_c2rust_label: {
        if (*result).magic_number == 0x72ec82d2 as ::core::ffi::c_int as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"result->magic_number == ALLOC_TEST_MAGIC\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/alloc-testing.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                78 as ::core::ffi::c_uint,
                b"BlockHeader *alloc_test_get_header(void *)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    return result;
}
unsafe extern "C" fn alloc_test_overwrite(
    mut ptr: *mut ::core::ffi::c_void,
    mut length: size_t,
    mut pattern: ::core::ffi::c_uint,
) {
    let mut byte_ptr: *mut ::core::ffi::c_uchar = ::core::ptr::null_mut::<::core::ffi::c_uchar>();
    let mut pattern_seq: ::core::ffi::c_int = 0;
    let mut b: ::core::ffi::c_uchar = 0;
    let mut i: size_t = 0;
    byte_ptr = ptr as *mut ::core::ffi::c_uchar;
    i = 0 as size_t;
    while i < length {
        pattern_seq = (i & 3 as size_t) as ::core::ffi::c_int;
        b = (pattern >> 8 as ::core::ffi::c_int * pattern_seq & 0xff as ::core::ffi::c_uint)
            as ::core::ffi::c_uchar;
        *byte_ptr.offset(i as isize) = b;
        i = i.wrapping_add(1);
    }
}
#[no_mangle]
pub unsafe extern "C" fn alloc_test_malloc(mut bytes: size_t) -> *mut ::core::ffi::c_void {
    let mut header: *mut BlockHeader = ::core::ptr::null_mut::<BlockHeader>();
    let mut ptr: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
    if allocation_limit == 0 as ::core::ffi::c_int {
        return NULL;
    }
    header = malloc((::core::mem::size_of::<BlockHeader>() as size_t).wrapping_add(bytes))
        as *mut BlockHeader;
    if header.is_null() {
        return NULL;
    }
    (*header).magic_number = ALLOC_TEST_MAGIC as ::core::ffi::c_uint;
    (*header).bytes = bytes;
    ptr = header.offset(1 as ::core::ffi::c_int as isize) as *mut ::core::ffi::c_void;
    alloc_test_overwrite(ptr, bytes, MALLOC_PATTERN);
    allocated_bytes = allocated_bytes.wrapping_add(bytes);
    if allocation_limit > 0 as ::core::ffi::c_int {
        allocation_limit -= 1;
    }
    return header.offset(1 as ::core::ffi::c_int as isize) as *mut ::core::ffi::c_void;
}
#[no_mangle]
pub unsafe extern "C" fn alloc_test_free(mut ptr: *mut ::core::ffi::c_void) {
    let mut header: *mut BlockHeader = ::core::ptr::null_mut::<BlockHeader>();
    let mut block_size: size_t = 0;
    if ptr.is_null() {
        return;
    }
    header = alloc_test_get_header(ptr);
    block_size = (*header).bytes;
    '_c2rust_label: {
        if allocated_bytes >= block_size {
        } else {
            __assert_fail(
                b"allocated_bytes >= block_size\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/alloc-testing.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                165 as ::core::ffi::c_uint,
                b"void alloc_test_free(void *)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_overwrite(ptr, (*header).bytes, FREE_PATTERN);
    (*header).magic_number = 0 as ::core::ffi::c_uint;
    free(header as *mut ::core::ffi::c_void);
    allocated_bytes = allocated_bytes.wrapping_sub(block_size);
}
#[no_mangle]
pub unsafe extern "C" fn alloc_test_realloc(
    mut ptr: *mut ::core::ffi::c_void,
    mut bytes: size_t,
) -> *mut ::core::ffi::c_void {
    let mut header: *mut BlockHeader = ::core::ptr::null_mut::<BlockHeader>();
    let mut new_ptr: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
    let mut bytes_to_copy: size_t = 0;
    new_ptr = alloc_test_malloc(bytes);
    if new_ptr.is_null() {
        return NULL;
    }
    if !ptr.is_null() {
        header = alloc_test_get_header(ptr);
        bytes_to_copy = (*header).bytes;
        if bytes_to_copy > bytes {
            bytes_to_copy = bytes;
        }
        memcpy(new_ptr, ptr, bytes_to_copy);
        alloc_test_free(ptr);
    }
    return new_ptr;
}
#[no_mangle]
pub unsafe extern "C" fn alloc_test_calloc(
    mut nmemb: size_t,
    mut bytes: size_t,
) -> *mut ::core::ffi::c_void {
    let mut result: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
    let mut total_bytes: size_t = nmemb.wrapping_mul(bytes);
    result = alloc_test_malloc(total_bytes);
    if result.is_null() {
        return NULL;
    }
    memset(result, 0 as ::core::ffi::c_int, total_bytes);
    return result;
}
#[no_mangle]
pub unsafe extern "C" fn alloc_test_strdup(
    mut string: *const ::core::ffi::c_char,
) -> *mut ::core::ffi::c_char {
    let mut result: *mut ::core::ffi::c_char = ::core::ptr::null_mut::<::core::ffi::c_char>();
    result =
        alloc_test_malloc(strlen(string).wrapping_add(1 as size_t)) as *mut ::core::ffi::c_char;
    if result.is_null() {
        return ::core::ptr::null_mut::<::core::ffi::c_char>();
    }
    strcpy(result, string);
    return result;
}
#[no_mangle]
pub unsafe extern "C" fn alloc_test_set_limit(mut alloc_count: ::core::ffi::c_int) {
    allocation_limit = alloc_count;
}
#[no_mangle]
pub unsafe extern "C" fn alloc_test_get_allocated() -> size_t {
    return allocated_bytes;
}
