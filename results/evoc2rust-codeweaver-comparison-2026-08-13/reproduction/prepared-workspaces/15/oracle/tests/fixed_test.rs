extern "C" {
    pub type _Trie;
    fn sprintf(
        __s: *mut ::core::ffi::c_char,
        __format: *const ::core::ffi::c_char,
        ...
    ) -> ::core::ffi::c_int;
    fn memset(
        __s: *mut ::core::ffi::c_void,
        __c: ::core::ffi::c_int,
        __n: size_t,
    ) -> *mut ::core::ffi::c_void;
    fn strcmp(
        __s1: *const ::core::ffi::c_char,
        __s2: *const ::core::ffi::c_char,
    ) -> ::core::ffi::c_int;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn alloc_test_get_allocated() -> size_t;
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn trie_new() -> *mut Trie;
    fn trie_free(trie: *mut Trie);
    fn trie_insert(
        trie: *mut Trie,
        key: *mut ::core::ffi::c_char,
        value: TrieValue,
    ) -> ::core::ffi::c_int;
    fn trie_insert_binary(
        trie: *mut Trie,
        key: *mut ::core::ffi::c_uchar,
        key_length: ::core::ffi::c_int,
        value: TrieValue,
    ) -> ::core::ffi::c_int;
    fn trie_lookup(trie: *mut Trie, key: *mut ::core::ffi::c_char) -> TrieValue;
    fn trie_lookup_binary(
        trie: *mut Trie,
        key: *mut ::core::ffi::c_uchar,
        key_length: ::core::ffi::c_int,
    ) -> TrieValue;
    fn trie_remove(trie: *mut Trie, key: *mut ::core::ffi::c_char) -> ::core::ffi::c_int;
    fn trie_remove_binary(
        trie: *mut Trie,
        key: *mut ::core::ffi::c_uchar,
        key_length: ::core::ffi::c_int,
    ) -> ::core::ffi::c_int;
    fn trie_num_entries(trie: *mut Trie) -> ::core::ffi::c_uint;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type Trie = _Trie;
pub type TrieValue = *mut ::core::ffi::c_void;
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
pub const NUM_TEST_VALUES: ::core::ffi::c_int = 10000 as ::core::ffi::c_int;
#[no_mangle]
pub static mut test_array: [::core::ffi::c_int; 10000] = [0; 10000];
#[no_mangle]
pub static mut test_strings: [[::core::ffi::c_char; 10]; 10000] = [[0; 10]; 10000];
#[no_mangle]
pub static mut bin_key: [::core::ffi::c_uchar; 7] = [
    'a' as i32 as ::core::ffi::c_uchar,
    'b' as i32 as ::core::ffi::c_uchar,
    'c' as i32 as ::core::ffi::c_uchar,
    0 as ::core::ffi::c_int as ::core::ffi::c_uchar,
    1 as ::core::ffi::c_int as ::core::ffi::c_uchar,
    2 as ::core::ffi::c_int as ::core::ffi::c_uchar,
    0xff as ::core::ffi::c_int as ::core::ffi::c_uchar,
];
#[no_mangle]
pub static mut bin_key2: [::core::ffi::c_uchar; 8] = [
    'a' as i32 as ::core::ffi::c_uchar,
    'b' as i32 as ::core::ffi::c_uchar,
    'c' as i32 as ::core::ffi::c_uchar,
    0 as ::core::ffi::c_int as ::core::ffi::c_uchar,
    1 as ::core::ffi::c_int as ::core::ffi::c_uchar,
    2 as ::core::ffi::c_int as ::core::ffi::c_uchar,
    0xff as ::core::ffi::c_int as ::core::ffi::c_uchar,
    0 as ::core::ffi::c_int as ::core::ffi::c_uchar,
];
#[no_mangle]
pub static mut bin_key3: [::core::ffi::c_uchar; 3] = [
    'a' as i32 as ::core::ffi::c_uchar,
    'b' as i32 as ::core::ffi::c_uchar,
    'c' as i32 as ::core::ffi::c_uchar,
];
#[no_mangle]
pub static mut bin_key4: [::core::ffi::c_uchar; 4] = [
    'z' as i32 as ::core::ffi::c_uchar,
    0 as ::core::ffi::c_int as ::core::ffi::c_uchar,
    'z' as i32 as ::core::ffi::c_uchar,
    'z' as i32 as ::core::ffi::c_uchar,
];
#[no_mangle]
pub unsafe extern "C" fn generate_trie() -> *mut Trie {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut i: ::core::ffi::c_int = 0;
    let mut entries: ::core::ffi::c_uint = 0;
    trie = trie_new();
    entries = 0 as ::core::ffi::c_uint;
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        test_array[i as usize] = i;
        sprintf(
            &raw mut *(&raw mut test_strings as *mut [::core::ffi::c_char; 10]).offset(i as isize)
                as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        '_c2rust_label: {
            if trie_insert(
                trie,
                &raw mut *(&raw mut test_strings as *mut [::core::ffi::c_char; 10])
                    .offset(i as isize) as *mut ::core::ffi::c_char,
                (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as TrieValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"trie_insert(trie, test_strings[i], &test_array[i]) != 0\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    60 as ::core::ffi::c_uint,
                    b"Trie *generate_trie(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        entries = entries.wrapping_add(1);
        '_c2rust_label_0: {
            if trie_num_entries(trie) == entries {
            } else {
                __assert_fail(
                    b"trie_num_entries(trie) == entries\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    64 as ::core::ffi::c_uint,
                    b"Trie *generate_trie(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    return trie;
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_new_free() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    trie = trie_new();
    '_c2rust_label: {
        if !trie.is_null() {
        } else {
            __assert_fail(
                b"trie != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                78 as ::core::ffi::c_uint,
                b"void test_trie_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
    trie = trie_new();
    '_c2rust_label_0: {
        if trie_insert(
            trie,
            b"hello\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            b"there\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"hello\", \"there\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                86 as ::core::ffi::c_uint,
                b"void test_trie_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if trie_insert(
            trie,
            b"hell\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            b"testing\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"hell\", \"testing\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                87 as ::core::ffi::c_uint,
                b"void test_trie_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if trie_insert(
            trie,
            b"testing\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            b"testing\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"testing\", \"testing\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                88 as ::core::ffi::c_uint,
                b"void test_trie_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if trie_insert(
            trie,
            b"\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            b"asfasf\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"\", \"asfasf\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                89 as ::core::ffi::c_uint,
                b"void test_trie_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
    trie = trie_new();
    '_c2rust_label_4: {
        if trie_insert(
            trie,
            b"hello\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            b"there\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"hello\", \"there\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                97 as ::core::ffi::c_uint,
                b"void test_trie_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if trie_remove(
            trie,
            b"hello\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove(trie, \"hello\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                98 as ::core::ffi::c_uint,
                b"void test_trie_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    trie = trie_new();
    '_c2rust_label_6: {
        if trie.is_null() {
        } else {
            __assert_fail(
                b"trie == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                106 as ::core::ffi::c_uint,
                b"void test_trie_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_insert() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut entries: ::core::ffi::c_uint = 0;
    let mut allocated: size_t = 0;
    trie = generate_trie();
    entries = trie_num_entries(trie);
    '_c2rust_label: {
        if trie_insert(
            trie,
            b"hello world\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            ::core::ptr::null_mut::<::core::ffi::c_void>(),
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"hello world\", NULL) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                120 as ::core::ffi::c_uint,
                b"void test_trie_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_num_entries(trie) == entries {
        } else {
            __assert_fail(
                b"trie_num_entries(trie) == entries\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                121 as ::core::ffi::c_uint,
                b"void test_trie_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    allocated = alloc_test_get_allocated();
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_1: {
        if trie_insert(
            trie,
            b"a\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            b"test value\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"a\", \"test value\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                127 as ::core::ffi::c_uint,
                b"void test_trie_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if trie_num_entries(trie) == entries {
        } else {
            __assert_fail(
                b"trie_num_entries(trie) == entries\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                128 as ::core::ffi::c_uint,
                b"void test_trie_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(5 as ::core::ffi::c_int);
    '_c2rust_label_3: {
        if trie_insert(
            trie,
            b"hello world\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            b"test value\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"hello world\", \"test value\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                133 as ::core::ffi::c_uint,
                b"void test_trie_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if alloc_test_get_allocated() == allocated {
        } else {
            __assert_fail(
                b"alloc_test_get_allocated() == allocated\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                134 as ::core::ffi::c_uint,
                b"void test_trie_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if trie_num_entries(trie) == entries {
        } else {
            __assert_fail(
                b"trie_num_entries(trie) == entries\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                135 as ::core::ffi::c_uint,
                b"void test_trie_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_lookup() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    trie = generate_trie();
    '_c2rust_label: {
        if trie_lookup(
            trie,
            b"000000000000000\0" as *const u8 as *const ::core::ffi::c_char
                as *mut ::core::ffi::c_char,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"trie_lookup(trie, \"000000000000000\") == TRIE_NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                151 as ::core::ffi::c_uint,
                b"void test_trie_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_lookup(
            trie,
            b"\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"trie_lookup(trie, \"\") == TRIE_NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                152 as ::core::ffi::c_uint,
                b"void test_trie_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        val =
            trie_lookup(trie, &raw mut buf as *mut ::core::ffi::c_char) as *mut ::core::ffi::c_int;
        '_c2rust_label_1: {
            if *val == i {
            } else {
                __assert_fail(
                    b"*val == i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    162 as ::core::ffi::c_uint,
                    b"void test_trie_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    trie_free(trie);
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_remove() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    let mut i: ::core::ffi::c_int = 0;
    let mut entries: ::core::ffi::c_uint = 0;
    trie = generate_trie();
    '_c2rust_label: {
        if trie_remove(
            trie,
            b"000000000000000\0" as *const u8 as *const ::core::ffi::c_char
                as *mut ::core::ffi::c_char,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove(trie, \"000000000000000\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                179 as ::core::ffi::c_uint,
                b"void test_trie_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_remove(
            trie,
            b"\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove(trie, \"\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                180 as ::core::ffi::c_uint,
                b"void test_trie_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entries = trie_num_entries(trie);
    '_c2rust_label_1: {
        if entries == 10000 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"entries == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                184 as ::core::ffi::c_uint,
                b"void test_trie_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        '_c2rust_label_2: {
            if trie_remove(trie, &raw mut buf as *mut ::core::ffi::c_char)
                != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"trie_remove(trie, buf) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    194 as ::core::ffi::c_uint,
                    b"void test_trie_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        entries = entries.wrapping_sub(1);
        '_c2rust_label_3: {
            if trie_num_entries(trie) == entries {
            } else {
                __assert_fail(
                    b"trie_num_entries(trie) == entries\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    196 as ::core::ffi::c_uint,
                    b"void test_trie_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    trie_free(trie);
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_replace() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    trie = generate_trie();
    val = alloc_test_malloc(::core::mem::size_of::<::core::ffi::c_int>() as size_t)
        as *mut ::core::ffi::c_int;
    *val = 999 as ::core::ffi::c_int;
    '_c2rust_label: {
        if trie_insert(
            trie,
            b"999\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            val as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"999\", val) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                213 as ::core::ffi::c_uint,
                b"void test_trie_replace(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_num_entries(trie) == 10000 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"trie_num_entries(trie) == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                214 as ::core::ffi::c_uint,
                b"void test_trie_replace(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if trie_lookup(
            trie,
            b"999\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
        ) == val as TrieValue
        {
        } else {
            __assert_fail(
                b"trie_lookup(trie, \"999\") == val\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                216 as ::core::ffi::c_uint,
                b"void test_trie_replace(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_free(val as *mut ::core::ffi::c_void);
    trie_free(trie);
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_insert_empty() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    trie = trie_new();
    '_c2rust_label: {
        if trie_insert(
            trie,
            b"\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
            &raw mut buf as *mut ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, \"\", buf) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                230 as ::core::ffi::c_uint,
                b"void test_trie_insert_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_num_entries(trie) != 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"trie_num_entries(trie) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                231 as ::core::ffi::c_uint,
                b"void test_trie_insert_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if trie_lookup(
            trie,
            b"\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
        ) == &raw mut buf as *mut ::core::ffi::c_char as TrieValue
        {
        } else {
            __assert_fail(
                b"trie_lookup(trie, \"\") == buf\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                232 as ::core::ffi::c_uint,
                b"void test_trie_insert_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if trie_remove(
            trie,
            b"\0" as *const u8 as *const ::core::ffi::c_char as *mut ::core::ffi::c_char,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove(trie, \"\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                233 as ::core::ffi::c_uint,
                b"void test_trie_insert_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if trie_num_entries(trie) == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"trie_num_entries(trie) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                235 as ::core::ffi::c_uint,
                b"void test_trie_insert_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
}
pub const LONG_STRING_LEN: ::core::ffi::c_int = 4096 as ::core::ffi::c_int;
unsafe extern "C" fn test_trie_free_long() {
    let mut long_string: *mut ::core::ffi::c_char = ::core::ptr::null_mut::<::core::ffi::c_char>();
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    long_string = alloc_test_malloc(LONG_STRING_LEN as size_t) as *mut ::core::ffi::c_char;
    memset(
        long_string as *mut ::core::ffi::c_void,
        'A' as i32,
        LONG_STRING_LEN as size_t,
    );
    *long_string.offset((LONG_STRING_LEN - 1 as ::core::ffi::c_int) as isize) =
        '\0' as i32 as ::core::ffi::c_char;
    trie = trie_new();
    trie_insert(trie, long_string, long_string as TrieValue);
    trie_free(trie);
    alloc_test_free(long_string as *mut ::core::ffi::c_void);
}
unsafe extern "C" fn test_trie_negative_keys() {
    let mut my_key: [::core::ffi::c_char; 6] = [
        'a' as i32 as ::core::ffi::c_char,
        'b' as i32 as ::core::ffi::c_char,
        'c' as i32 as ::core::ffi::c_char,
        -(50 as ::core::ffi::c_int) as ::core::ffi::c_char,
        -(20 as ::core::ffi::c_int) as ::core::ffi::c_char,
        '\0' as i32 as ::core::ffi::c_char,
    ];
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut value: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
    trie = trie_new();
    '_c2rust_label: {
        if trie_insert(
            trie,
            &raw mut my_key as *mut ::core::ffi::c_char,
            b"hello world\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert(trie, my_key, \"hello world\") != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                273 as ::core::ffi::c_uint,
                b"void test_trie_negative_keys(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    value =
        trie_lookup(trie, &raw mut my_key as *mut ::core::ffi::c_char) as *mut ::core::ffi::c_void;
    '_c2rust_label_0: {
        if strcmp(
            value as *const ::core::ffi::c_char,
            b"hello world\0" as *const u8 as *const ::core::ffi::c_char,
        ) == 0
        {
        } else {
            __assert_fail(
                b"!strcmp(value, \"hello world\")\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                277 as ::core::ffi::c_uint,
                b"void test_trie_negative_keys(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if trie_remove(trie, &raw mut my_key as *mut ::core::ffi::c_char) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove(trie, my_key) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                279 as ::core::ffi::c_uint,
                b"void test_trie_negative_keys(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if trie_remove(trie, &raw mut my_key as *mut ::core::ffi::c_char) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove(trie, my_key) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                280 as ::core::ffi::c_uint,
                b"void test_trie_negative_keys(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if trie_lookup(trie, &raw mut my_key as *mut ::core::ffi::c_char).is_null() {
        } else {
            __assert_fail(
                b"trie_lookup(trie, my_key) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                281 as ::core::ffi::c_uint,
                b"void test_trie_negative_keys(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
}
#[no_mangle]
pub unsafe extern "C" fn generate_binary_trie() -> *mut Trie {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    trie = trie_new();
    '_c2rust_label: {
        if trie_insert_binary(
            trie,
            &raw mut bin_key2 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 8]>() as ::core::ffi::c_int,
            b"goodbye world\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert_binary(trie, bin_key2, sizeof(bin_key2), \"goodbye world\") != 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                296 as ::core::ffi::c_uint,
                b"Trie *generate_binary_trie(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_insert_binary(
            trie,
            &raw mut bin_key as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 7]>() as ::core::ffi::c_int,
            b"hello world\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert_binary(trie, bin_key, sizeof(bin_key), \"hello world\") != 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                299 as ::core::ffi::c_uint,
                b"Trie *generate_binary_trie(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    return trie;
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_insert_binary() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut value: *mut ::core::ffi::c_char = ::core::ptr::null_mut::<::core::ffi::c_char>();
    trie = generate_binary_trie();
    '_c2rust_label: {
        if trie_insert_binary(
            trie,
            &raw mut bin_key as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 7]>() as ::core::ffi::c_int,
            b"hi world\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert_binary(trie, bin_key, sizeof(bin_key), \"hi world\") != 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                315 as ::core::ffi::c_uint,
                b"void test_trie_insert_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_insert_binary(
            trie,
            &raw mut bin_key3 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 3]>() as ::core::ffi::c_int,
            ::core::ptr::null_mut::<::core::ffi::c_void>(),
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert_binary(trie, bin_key3, sizeof(bin_key3), NULL) == 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                320 as ::core::ffi::c_uint,
                b"void test_trie_insert_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    value = trie_lookup_binary(
        trie,
        &raw mut bin_key as *mut ::core::ffi::c_uchar,
        ::core::mem::size_of::<[::core::ffi::c_uchar; 7]>() as ::core::ffi::c_int,
    ) as *mut ::core::ffi::c_char;
    '_c2rust_label_1: {
        if strcmp(
            value,
            b"hi world\0" as *const u8 as *const ::core::ffi::c_char,
        ) == 0
        {
        } else {
            __assert_fail(
                b"!strcmp(value, \"hi world\")\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                325 as ::core::ffi::c_uint,
                b"void test_trie_insert_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    value = trie_lookup_binary(
        trie,
        &raw mut bin_key2 as *mut ::core::ffi::c_uchar,
        ::core::mem::size_of::<[::core::ffi::c_uchar; 8]>() as ::core::ffi::c_int,
    ) as *mut ::core::ffi::c_char;
    '_c2rust_label_2: {
        if strcmp(
            value,
            b"goodbye world\0" as *const u8 as *const ::core::ffi::c_char,
        ) == 0
        {
        } else {
            __assert_fail(
                b"!strcmp(value, \"goodbye world\")\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                328 as ::core::ffi::c_uint,
                b"void test_trie_insert_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_insert_out_of_memory() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    trie = generate_binary_trie();
    alloc_test_set_limit(3 as ::core::ffi::c_int);
    '_c2rust_label: {
        if trie_insert_binary(
            trie,
            &raw mut bin_key4 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 4]>() as ::core::ffi::c_int,
            b"test value\0" as *const u8 as *const ::core::ffi::c_char as TrieValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_insert_binary(trie, bin_key4, sizeof(bin_key4), \"test value\") == 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                343 as ::core::ffi::c_uint,
                b"void test_trie_insert_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_lookup_binary(
            trie,
            &raw mut bin_key4 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 4]>() as ::core::ffi::c_int,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"trie_lookup_binary(trie, bin_key4, sizeof(bin_key4)) == NULL\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                345 as ::core::ffi::c_uint,
                b"void test_trie_insert_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if trie_num_entries(trie) == 2 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"trie_num_entries(trie) == 2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                346 as ::core::ffi::c_uint,
                b"void test_trie_insert_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
}
#[no_mangle]
pub unsafe extern "C" fn test_trie_remove_binary() {
    let mut trie: *mut Trie = ::core::ptr::null_mut::<Trie>();
    let mut value: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
    trie = generate_binary_trie();
    value = trie_lookup_binary(
        trie,
        &raw mut bin_key3 as *mut ::core::ffi::c_uchar,
        ::core::mem::size_of::<[::core::ffi::c_uchar; 3]>() as ::core::ffi::c_int,
    ) as *mut ::core::ffi::c_void;
    '_c2rust_label: {
        if value.is_null() {
        } else {
            __assert_fail(
                b"value == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                361 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if trie_remove_binary(
            trie,
            &raw mut bin_key3 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 3]>() as ::core::ffi::c_int,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove_binary(trie, bin_key3, sizeof(bin_key3)) == 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                363 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if trie_lookup_binary(
            trie,
            &raw mut bin_key4 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 4]>() as ::core::ffi::c_int,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"trie_lookup_binary(trie, bin_key4, sizeof(bin_key4)) == 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                365 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if trie_remove_binary(
            trie,
            &raw mut bin_key4 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 4]>() as ::core::ffi::c_int,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove_binary(trie, bin_key4, sizeof(bin_key4)) == 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                366 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if trie_remove_binary(
            trie,
            &raw mut bin_key2 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 8]>() as ::core::ffi::c_int,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove_binary(trie, bin_key2, sizeof(bin_key2)) != 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                370 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if trie_lookup_binary(
            trie,
            &raw mut bin_key2 as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 8]>() as ::core::ffi::c_int,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"trie_lookup_binary(trie, bin_key2, sizeof(bin_key2)) == NULL\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                371 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if !trie_lookup_binary(
            trie,
            &raw mut bin_key as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 7]>() as ::core::ffi::c_int,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"trie_lookup_binary(trie, bin_key, sizeof(bin_key)) != NULL\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                372 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if trie_remove_binary(
            trie,
            &raw mut bin_key as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 7]>() as ::core::ffi::c_int,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"trie_remove_binary(trie, bin_key, sizeof(bin_key)) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                374 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if trie_lookup_binary(
            trie,
            &raw mut bin_key as *mut ::core::ffi::c_uchar,
            ::core::mem::size_of::<[::core::ffi::c_uchar; 7]>() as ::core::ffi::c_int,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"trie_lookup_binary(trie, bin_key, sizeof(bin_key)) == NULL\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-trie.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                375 as ::core::ffi::c_uint,
                b"void test_trie_remove_binary(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    trie_free(trie);
}
static mut tests: [UnitTestFunction; 12] = unsafe {
    [
        Some(test_trie_new_free as unsafe extern "C" fn() -> ()),
        Some(test_trie_insert as unsafe extern "C" fn() -> ()),
        Some(test_trie_lookup as unsafe extern "C" fn() -> ()),
        Some(test_trie_remove as unsafe extern "C" fn() -> ()),
        Some(test_trie_replace as unsafe extern "C" fn() -> ()),
        Some(test_trie_insert_empty as unsafe extern "C" fn() -> ()),
        Some(test_trie_free_long as unsafe extern "C" fn() -> ()),
        Some(test_trie_negative_keys as unsafe extern "C" fn() -> ()),
        Some(test_trie_insert_binary as unsafe extern "C" fn() -> ()),
        Some(test_trie_insert_out_of_memory as unsafe extern "C" fn() -> ()),
        Some(test_trie_remove_binary as unsafe extern "C" fn() -> ()),
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
