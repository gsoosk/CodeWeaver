extern "C" {
    pub type _BloomFilter;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn bloom_filter_new(
        table_size: ::core::ffi::c_uint,
        hash_func: BloomFilterHashFunc,
        num_functions: ::core::ffi::c_uint,
    ) -> *mut BloomFilter;
    fn bloom_filter_free(bloomfilter: *mut BloomFilter);
    fn bloom_filter_insert(bloomfilter: *mut BloomFilter, value: BloomFilterValue);
    fn bloom_filter_query(
        bloomfilter: *mut BloomFilter,
        value: BloomFilterValue,
    ) -> ::core::ffi::c_int;
    fn bloom_filter_read(bloomfilter: *mut BloomFilter, array: *mut ::core::ffi::c_uchar);
    fn bloom_filter_load(bloomfilter: *mut BloomFilter, array: *mut ::core::ffi::c_uchar);
    fn bloom_filter_union(filter1: *mut BloomFilter, filter2: *mut BloomFilter)
        -> *mut BloomFilter;
    fn bloom_filter_intersection(
        filter1: *mut BloomFilter,
        filter2: *mut BloomFilter,
    ) -> *mut BloomFilter;
    fn string_hash(string: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
    fn string_nocase_hash(string: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
}
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type BloomFilter = _BloomFilter;
pub type BloomFilterValue = *mut ::core::ffi::c_void;
pub type BloomFilterHashFunc =
    Option<unsafe extern "C" fn(BloomFilterValue) -> ::core::ffi::c_uint>;
pub const NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
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
#[no_mangle]
pub unsafe extern "C" fn test_bloom_filter_new_free() {
    let mut filter: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    filter = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        1 as ::core::ffi::c_uint,
    );
    '_c2rust_label: {
        if !filter.is_null() {
        } else {
            __assert_fail(
                b"filter != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                39 as ::core::ffi::c_uint,
                b"void test_bloom_filter_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter);
    filter = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        64 as ::core::ffi::c_uint,
    );
    '_c2rust_label_0: {
        if !filter.is_null() {
        } else {
            __assert_fail(
                b"filter != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                47 as ::core::ffi::c_uint,
                b"void test_bloom_filter_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter);
    filter = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        50000 as ::core::ffi::c_uint,
    );
    '_c2rust_label_1: {
        if filter.is_null() {
        } else {
            __assert_fail(
                b"filter == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                55 as ::core::ffi::c_uint,
                b"void test_bloom_filter_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    filter = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        1 as ::core::ffi::c_uint,
    );
    '_c2rust_label_2: {
        if filter.is_null() {
        } else {
            __assert_fail(
                b"filter == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                63 as ::core::ffi::c_uint,
                b"void test_bloom_filter_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(1 as ::core::ffi::c_int);
    filter = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        1 as ::core::ffi::c_uint,
    );
    '_c2rust_label_3: {
        if filter.is_null() {
        } else {
            __assert_fail(
                b"filter == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                69 as ::core::ffi::c_uint,
                b"void test_bloom_filter_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_bloom_filter_insert_query() {
    let mut filter: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    filter = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    '_c2rust_label: {
        if bloom_filter_query(
            filter,
            b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(filter, \"test 1\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                82 as ::core::ffi::c_uint,
                b"void test_bloom_filter_insert_query(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if bloom_filter_query(
            filter,
            b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(filter, \"test 2\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                83 as ::core::ffi::c_uint,
                b"void test_bloom_filter_insert_query(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_insert(
        filter,
        b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    bloom_filter_insert(
        filter,
        b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    '_c2rust_label_1: {
        if bloom_filter_query(
            filter,
            b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(filter, \"test 1\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                92 as ::core::ffi::c_uint,
                b"void test_bloom_filter_insert_query(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if bloom_filter_query(
            filter,
            b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(filter, \"test 2\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                93 as ::core::ffi::c_uint,
                b"void test_bloom_filter_insert_query(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter);
}
#[no_mangle]
pub unsafe extern "C" fn test_bloom_filter_read_load() {
    let mut filter1: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    let mut filter2: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    let mut state: [::core::ffi::c_uchar; 16] = [0; 16];
    filter1 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    bloom_filter_insert(
        filter1,
        b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    bloom_filter_insert(
        filter1,
        b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    bloom_filter_read(filter1, &raw mut state as *mut ::core::ffi::c_uchar);
    bloom_filter_free(filter1);
    filter2 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    bloom_filter_load(filter2, &raw mut state as *mut ::core::ffi::c_uchar);
    '_c2rust_label: {
        if bloom_filter_query(
            filter2,
            b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(filter2, \"test 1\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                125 as ::core::ffi::c_uint,
                b"void test_bloom_filter_read_load(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if bloom_filter_query(
            filter2,
            b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(filter2, \"test 2\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                126 as ::core::ffi::c_uint,
                b"void test_bloom_filter_read_load(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter2);
}
#[no_mangle]
pub unsafe extern "C" fn test_bloom_filter_intersection() {
    let mut filter1: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    let mut filter2: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    let mut result: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    filter1 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    bloom_filter_insert(
        filter1,
        b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    bloom_filter_insert(
        filter1,
        b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    filter2 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    bloom_filter_insert(
        filter2,
        b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    '_c2rust_label: {
        if bloom_filter_query(
            filter2,
            b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(filter2, \"test 2\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                154 as ::core::ffi::c_uint,
                b"void test_bloom_filter_intersection(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    result = bloom_filter_intersection(filter1, filter2);
    '_c2rust_label_0: {
        if bloom_filter_query(
            result,
            b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(result, \"test 1\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                163 as ::core::ffi::c_uint,
                b"void test_bloom_filter_intersection(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if bloom_filter_query(
            result,
            b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(result, \"test 2\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                164 as ::core::ffi::c_uint,
                b"void test_bloom_filter_intersection(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(result);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    result = bloom_filter_intersection(filter1, filter2);
    '_c2rust_label_2: {
        if result.is_null() {
        } else {
            __assert_fail(
                b"result == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                172 as ::core::ffi::c_uint,
                b"void test_bloom_filter_intersection(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter1);
    bloom_filter_free(filter2);
}
#[no_mangle]
pub unsafe extern "C" fn test_bloom_filter_union() {
    let mut filter1: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    let mut filter2: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    let mut result: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    filter1 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    bloom_filter_insert(
        filter1,
        b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    filter2 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    bloom_filter_insert(
        filter2,
        b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
    );
    result = bloom_filter_union(filter1, filter2);
    '_c2rust_label: {
        if bloom_filter_query(
            result,
            b"test 1\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(result, \"test 1\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                202 as ::core::ffi::c_uint,
                b"void test_bloom_filter_union(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if bloom_filter_query(
            result,
            b"test 2\0" as *const u8 as *const ::core::ffi::c_char as BloomFilterValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"bloom_filter_query(result, \"test 2\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                203 as ::core::ffi::c_uint,
                b"void test_bloom_filter_union(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(result);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    result = bloom_filter_union(filter1, filter2);
    '_c2rust_label_1: {
        if result.is_null() {
        } else {
            __assert_fail(
                b"result == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                211 as ::core::ffi::c_uint,
                b"void test_bloom_filter_union(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter1);
    bloom_filter_free(filter2);
}
#[no_mangle]
pub unsafe extern "C" fn test_bloom_filter_mismatch() {
    let mut filter1: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    let mut filter2: *mut BloomFilter = ::core::ptr::null_mut::<BloomFilter>();
    filter1 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    filter2 = bloom_filter_new(
        64 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        4 as ::core::ffi::c_uint,
    );
    '_c2rust_label: {
        if bloom_filter_intersection(filter1, filter2).is_null() {
        } else {
            __assert_fail(
                b"bloom_filter_intersection(filter1, filter2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                231 as ::core::ffi::c_uint,
                b"void test_bloom_filter_mismatch(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if bloom_filter_union(filter1, filter2).is_null() {
        } else {
            __assert_fail(
                b"bloom_filter_union(filter1, filter2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                232 as ::core::ffi::c_uint,
                b"void test_bloom_filter_mismatch(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter2);
    filter2 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(
            string_nocase_hash
                as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint,
        ),
        4 as ::core::ffi::c_uint,
    );
    '_c2rust_label_1: {
        if bloom_filter_intersection(filter1, filter2).is_null() {
        } else {
            __assert_fail(
                b"bloom_filter_intersection(filter1, filter2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                238 as ::core::ffi::c_uint,
                b"void test_bloom_filter_mismatch(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if bloom_filter_union(filter1, filter2).is_null() {
        } else {
            __assert_fail(
                b"bloom_filter_union(filter1, filter2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                239 as ::core::ffi::c_uint,
                b"void test_bloom_filter_mismatch(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter2);
    filter2 = bloom_filter_new(
        128 as ::core::ffi::c_uint,
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        32 as ::core::ffi::c_uint,
    );
    '_c2rust_label_3: {
        if bloom_filter_intersection(filter1, filter2).is_null() {
        } else {
            __assert_fail(
                b"bloom_filter_intersection(filter1, filter2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                245 as ::core::ffi::c_uint,
                b"void test_bloom_filter_mismatch(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if bloom_filter_union(filter1, filter2).is_null() {
        } else {
            __assert_fail(
                b"bloom_filter_union(filter1, filter2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-bloom-filter.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                246 as ::core::ffi::c_uint,
                b"void test_bloom_filter_mismatch(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    bloom_filter_free(filter2);
    bloom_filter_free(filter1);
}
static mut tests: [UnitTestFunction; 7] = unsafe {
    [
        Some(test_bloom_filter_new_free as unsafe extern "C" fn() -> ()),
        Some(test_bloom_filter_insert_query as unsafe extern "C" fn() -> ()),
        Some(test_bloom_filter_read_load as unsafe extern "C" fn() -> ()),
        Some(test_bloom_filter_intersection as unsafe extern "C" fn() -> ()),
        Some(test_bloom_filter_union as unsafe extern "C" fn() -> ()),
        Some(test_bloom_filter_mismatch as unsafe extern "C" fn() -> ()),
        None,
    ]
};
unsafe fn main_0(
    mut argc: ::core::ffi::c_int,
    mut argv: *mut *mut ::core::ffi::c_char,
) -> ::core::ffi::c_int {
    run_tests(&raw mut tests as *mut UnitTestFunction);
    return 0 as ::core::ffi::c_int;
}
pub fn main() {
    let mut args_strings: Vec<Vec<u8>> = ::std::env::args()
        .map(|arg| {
            ::std::ffi::CString::new(arg)
                .expect("Failed to convert argument into CString.")
                .into_bytes_with_nul()
        })
        .collect();
    let mut args_ptrs: Vec<*mut ::core::ffi::c_char> = args_strings
        .iter_mut()
        .map(|arg| arg.as_mut_ptr() as *mut ::core::ffi::c_char)
        .chain(::core::iter::once(::core::ptr::null_mut()))
        .collect();
    unsafe {
        ::std::process::exit(main_0(
            (args_ptrs.len() - 1) as ::core::ffi::c_int,
            args_ptrs.as_mut_ptr() as *mut *mut ::core::ffi::c_char,
        ) as i32)
    }
}
