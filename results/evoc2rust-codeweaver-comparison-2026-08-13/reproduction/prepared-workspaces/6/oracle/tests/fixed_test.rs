extern "C" {
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn int_equal(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn int_compare(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn pointer_equal(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn pointer_compare(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn string_equal(
        string1: *mut ::core::ffi::c_void,
        string2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn string_compare(
        string1: *mut ::core::ffi::c_void,
        string2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn string_nocase_equal(
        string1: *mut ::core::ffi::c_void,
        string2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn string_nocase_compare(
        string1: *mut ::core::ffi::c_void,
        string2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
}
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
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
pub unsafe extern "C" fn test_int_compare() {
    let mut a: ::core::ffi::c_int = 4 as ::core::ffi::c_int;
    let mut b: ::core::ffi::c_int = 8 as ::core::ffi::c_int;
    let mut c: ::core::ffi::c_int = 4 as ::core::ffi::c_int;
    '_c2rust_label: {
        if int_compare(
            &raw mut a as *mut ::core::ffi::c_void,
            &raw mut b as *mut ::core::ffi::c_void,
        ) < 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"int_compare(&a, &b) < 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                42 as ::core::ffi::c_uint,
                b"void test_int_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if int_compare(
            &raw mut b as *mut ::core::ffi::c_void,
            &raw mut a as *mut ::core::ffi::c_void,
        ) > 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"int_compare(&b, &a) > 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                46 as ::core::ffi::c_uint,
                b"void test_int_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if int_compare(
            &raw mut a as *mut ::core::ffi::c_void,
            &raw mut c as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"int_compare(&a, &c) == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                50 as ::core::ffi::c_uint,
                b"void test_int_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_int_equal() {
    let mut a: ::core::ffi::c_int = 4 as ::core::ffi::c_int;
    let mut b: ::core::ffi::c_int = 8 as ::core::ffi::c_int;
    let mut c: ::core::ffi::c_int = 4 as ::core::ffi::c_int;
    '_c2rust_label: {
        if int_equal(
            &raw mut a as *mut ::core::ffi::c_void,
            &raw mut c as *mut ::core::ffi::c_void,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"int_equal(&a, &c) != 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                61 as ::core::ffi::c_uint,
                b"void test_int_equal(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if int_equal(
            &raw mut a as *mut ::core::ffi::c_void,
            &raw mut b as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"int_equal(&a, &b) == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                65 as ::core::ffi::c_uint,
                b"void test_int_equal(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_pointer_compare() {
    let mut array: [::core::ffi::c_int; 5] = [0; 5];
    '_c2rust_label: {
        if pointer_compare(
            (&raw mut array as *mut ::core::ffi::c_int).offset(0 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
            (&raw mut array as *mut ::core::ffi::c_int).offset(4 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
        ) < 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"pointer_compare(&array[0], &array[4]) < 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                75 as ::core::ffi::c_uint,
                b"void test_pointer_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if pointer_compare(
            (&raw mut array as *mut ::core::ffi::c_int).offset(3 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
            (&raw mut array as *mut ::core::ffi::c_int).offset(2 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
        ) > 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"pointer_compare(&array[3], &array[2]) > 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                80 as ::core::ffi::c_uint,
                b"void test_pointer_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if pointer_compare(
            (&raw mut array as *mut ::core::ffi::c_int).offset(4 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
            (&raw mut array as *mut ::core::ffi::c_int).offset(4 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"pointer_compare(&array[4], &array[4]) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                84 as ::core::ffi::c_uint,
                b"void test_pointer_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_pointer_equal() {
    let mut a: ::core::ffi::c_int = 0;
    let mut b: ::core::ffi::c_int = 0;
    '_c2rust_label: {
        if pointer_equal(
            &raw mut a as *mut ::core::ffi::c_void,
            &raw mut a as *mut ::core::ffi::c_void,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"pointer_equal(&a, &a) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                93 as ::core::ffi::c_uint,
                b"void test_pointer_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if pointer_equal(
            &raw mut a as *mut ::core::ffi::c_void,
            &raw mut b as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"pointer_equal(&a, &b) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                97 as ::core::ffi::c_uint,
                b"void test_pointer_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_string_compare() {
    let mut test1: [::core::ffi::c_char; 6] =
        ::core::mem::transmute::<[u8; 6], [::core::ffi::c_char; 6]>(*b"Apple\0");
    let mut test2: [::core::ffi::c_char; 7] =
        ::core::mem::transmute::<[u8; 7], [::core::ffi::c_char; 7]>(*b"Orange\0");
    let mut test3: [::core::ffi::c_char; 6] =
        ::core::mem::transmute::<[u8; 6], [::core::ffi::c_char; 6]>(*b"Apple\0");
    '_c2rust_label: {
        if string_compare(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test2 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) < 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_compare(test1, test2) < 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                108 as ::core::ffi::c_uint,
                b"void test_string_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if string_compare(
            &raw mut test2 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) > 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_compare(test2, test1) > 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                112 as ::core::ffi::c_uint,
                b"void test_string_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if string_compare(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test3 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_compare(test1, test3) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                116 as ::core::ffi::c_uint,
                b"void test_string_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_string_equal() {
    let mut test1: [::core::ffi::c_char; 22] =
        ::core::mem::transmute::<[u8; 22], [::core::ffi::c_char; 22]>(*b"this is a test string\0");
    let mut test2: [::core::ffi::c_char; 23] =
        ::core::mem::transmute::<[u8; 23], [::core::ffi::c_char; 23]>(*b"this is a test string \0");
    let mut test3: [::core::ffi::c_char; 21] =
        ::core::mem::transmute::<[u8; 21], [::core::ffi::c_char; 21]>(*b"this is a test strin\0");
    let mut test4: [::core::ffi::c_char; 22] =
        ::core::mem::transmute::<[u8; 22], [::core::ffi::c_char; 22]>(*b"this is a test strinG\0");
    let mut test5: [::core::ffi::c_char; 22] =
        ::core::mem::transmute::<[u8; 22], [::core::ffi::c_char; 22]>(*b"this is a test string\0");
    '_c2rust_label: {
        if string_equal(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test5 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_equal(test1, test5) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                129 as ::core::ffi::c_uint,
                b"void test_string_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if string_equal(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test2 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_equal(test1, test2) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                134 as ::core::ffi::c_uint,
                b"void test_string_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if string_equal(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test3 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_equal(test1, test3) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                135 as ::core::ffi::c_uint,
                b"void test_string_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if string_equal(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test4 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_equal(test1, test4) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                138 as ::core::ffi::c_uint,
                b"void test_string_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_string_nocase_compare() {
    let mut test1: [::core::ffi::c_char; 6] =
        ::core::mem::transmute::<[u8; 6], [::core::ffi::c_char; 6]>(*b"Apple\0");
    let mut test2: [::core::ffi::c_char; 7] =
        ::core::mem::transmute::<[u8; 7], [::core::ffi::c_char; 7]>(*b"Orange\0");
    let mut test3: [::core::ffi::c_char; 6] =
        ::core::mem::transmute::<[u8; 6], [::core::ffi::c_char; 6]>(*b"Apple\0");
    let mut test4: [::core::ffi::c_char; 6] =
        ::core::mem::transmute::<[u8; 6], [::core::ffi::c_char; 6]>(*b"Alpha\0");
    let mut test5: [::core::ffi::c_char; 6] =
        ::core::mem::transmute::<[u8; 6], [::core::ffi::c_char; 6]>(*b"bravo\0");
    let mut test6: [::core::ffi::c_char; 8] =
        ::core::mem::transmute::<[u8; 8], [::core::ffi::c_char; 8]>(*b"Charlie\0");
    '_c2rust_label: {
        if string_nocase_compare(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test2 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) < 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_compare(test1, test2) < 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                152 as ::core::ffi::c_uint,
                b"void test_string_nocase_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if string_nocase_compare(
            &raw mut test2 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) > 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_compare(test2, test1) > 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                156 as ::core::ffi::c_uint,
                b"void test_string_nocase_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if string_nocase_compare(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test3 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_compare(test1, test3) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                160 as ::core::ffi::c_uint,
                b"void test_string_nocase_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if string_nocase_compare(
            &raw mut test4 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test5 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) < 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_compare(test4, test5) < 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                164 as ::core::ffi::c_uint,
                b"void test_string_nocase_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if string_nocase_compare(
            &raw mut test5 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test6 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) < 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_compare(test5, test6) < 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                165 as ::core::ffi::c_uint,
                b"void test_string_nocase_compare(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_string_nocase_equal() {
    let mut test1: [::core::ffi::c_char; 22] =
        ::core::mem::transmute::<[u8; 22], [::core::ffi::c_char; 22]>(*b"this is a test string\0");
    let mut test2: [::core::ffi::c_char; 23] =
        ::core::mem::transmute::<[u8; 23], [::core::ffi::c_char; 23]>(*b"this is a test string \0");
    let mut test3: [::core::ffi::c_char; 21] =
        ::core::mem::transmute::<[u8; 21], [::core::ffi::c_char; 21]>(*b"this is a test strin\0");
    let mut test4: [::core::ffi::c_char; 22] =
        ::core::mem::transmute::<[u8; 22], [::core::ffi::c_char; 22]>(*b"this is a test strinG\0");
    let mut test5: [::core::ffi::c_char; 22] =
        ::core::mem::transmute::<[u8; 22], [::core::ffi::c_char; 22]>(*b"this is a test string\0");
    '_c2rust_label: {
        if string_nocase_equal(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test5 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_equal(test1, test5) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                178 as ::core::ffi::c_uint,
                b"void test_string_nocase_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if string_nocase_equal(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test2 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_equal(test1, test2) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                183 as ::core::ffi::c_uint,
                b"void test_string_nocase_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if string_nocase_equal(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test3 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_equal(test1, test3) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                184 as ::core::ffi::c_uint,
                b"void test_string_nocase_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if string_nocase_equal(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
            &raw mut test4 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"string_nocase_equal(test1, test4) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-compare-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                187 as ::core::ffi::c_uint,
                b"void test_string_nocase_equal(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
static mut tests: [UnitTestFunction; 9] = unsafe {
    [
        Some(test_int_compare as unsafe extern "C" fn() -> ()),
        Some(test_int_equal as unsafe extern "C" fn() -> ()),
        Some(test_pointer_compare as unsafe extern "C" fn() -> ()),
        Some(test_pointer_equal as unsafe extern "C" fn() -> ()),
        Some(test_string_compare as unsafe extern "C" fn() -> ()),
        Some(test_string_equal as unsafe extern "C" fn() -> ()),
        Some(test_string_nocase_compare as unsafe extern "C" fn() -> ()),
        Some(test_string_nocase_equal as unsafe extern "C" fn() -> ()),
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
