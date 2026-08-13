extern "C" {
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn pointer_hash(location: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
    fn int_hash(location: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
    fn string_hash(string: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
    fn string_nocase_hash(string: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
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
pub const NUM_TEST_VALUES: ::core::ffi::c_int = 200 as ::core::ffi::c_int;
#[no_mangle]
pub unsafe extern "C" fn test_pointer_hash() {
    let mut array: [::core::ffi::c_int; 200] = [0; 200];
    let mut i: ::core::ffi::c_int = 0;
    let mut j: ::core::ffi::c_int = 0;
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        array[i as usize] = 0 as ::core::ffi::c_int;
        i += 1;
    }
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        j = i + 1 as ::core::ffi::c_int;
        while j < NUM_TEST_VALUES {
            '_c2rust_label: {
                if pointer_hash(
                    (&raw mut array as *mut ::core::ffi::c_int).offset(i as isize)
                        as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
                ) != pointer_hash(
                    (&raw mut array as *mut ::core::ffi::c_int).offset(j as isize)
                        as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
                ) {
                } else {
                    __assert_fail(
                        b"pointer_hash(&array[i]) != pointer_hash(&array[j])\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        50 as ::core::ffi::c_uint,
                        b"void test_pointer_hash(void)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
            j += 1;
        }
        i += 1;
    }
}
#[no_mangle]
pub unsafe extern "C" fn test_int_hash() {
    let mut array: [::core::ffi::c_int; 200] = [0; 200];
    let mut i: ::core::ffi::c_int = 0;
    let mut j: ::core::ffi::c_int = 0;
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        array[i as usize] = i;
        i += 1;
    }
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        j = i + 1 as ::core::ffi::c_int;
        while j < NUM_TEST_VALUES {
            '_c2rust_label: {
                if int_hash(
                    (&raw mut array as *mut ::core::ffi::c_int).offset(i as isize)
                        as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
                ) != int_hash(
                    (&raw mut array as *mut ::core::ffi::c_int).offset(j as isize)
                        as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
                ) {
                } else {
                    __assert_fail(
                        b"int_hash(&array[i]) != int_hash(&array[j])\0" as *const u8
                            as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        70 as ::core::ffi::c_uint,
                        b"void test_int_hash(void)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
            j += 1;
        }
        i += 1;
    }
    i = 5000 as ::core::ffi::c_int;
    j = 5000 as ::core::ffi::c_int;
    '_c2rust_label_0: {
        if int_hash(&raw mut i as *mut ::core::ffi::c_void)
            == int_hash(&raw mut j as *mut ::core::ffi::c_void)
        {
        } else {
            __assert_fail(
                b"int_hash(&i) == int_hash(&j)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                79 as ::core::ffi::c_uint,
                b"void test_int_hash(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_string_hash() {
    let mut test1: [::core::ffi::c_char; 15] =
        ::core::mem::transmute::<[u8; 15], [::core::ffi::c_char; 15]>(*b"this is a test\0");
    let mut test2: [::core::ffi::c_char; 15] =
        ::core::mem::transmute::<[u8; 15], [::core::ffi::c_char; 15]>(*b"this is a tesu\0");
    let mut test3: [::core::ffi::c_char; 16] =
        ::core::mem::transmute::<[u8; 16], [::core::ffi::c_char; 16]>(*b"this is a test \0");
    let mut test4: [::core::ffi::c_char; 15] =
        ::core::mem::transmute::<[u8; 15], [::core::ffi::c_char; 15]>(*b"this is a test\0");
    let mut test5: [::core::ffi::c_char; 15] =
        ::core::mem::transmute::<[u8; 15], [::core::ffi::c_char; 15]>(*b"This is a test\0");
    '_c2rust_label: {
        if string_hash(&raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void)
            != string_hash(&raw mut test2 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void)
        {
        } else {
            __assert_fail(
                b"string_hash(test1) != string_hash(test2)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                92 as ::core::ffi::c_uint,
                b"void test_string_hash(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if string_hash(&raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void)
            != string_hash(&raw mut test3 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void)
        {
        } else {
            __assert_fail(
                b"string_hash(test1) != string_hash(test3)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                96 as ::core::ffi::c_uint,
                b"void test_string_hash(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if string_hash(&raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void)
            != string_hash(&raw mut test5 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void)
        {
        } else {
            __assert_fail(
                b"string_hash(test1) != string_hash(test5)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                100 as ::core::ffi::c_uint,
                b"void test_string_hash(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if string_hash(&raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void)
            == string_hash(&raw mut test4 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void)
        {
        } else {
            __assert_fail(
                b"string_hash(test1) == string_hash(test4)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                104 as ::core::ffi::c_uint,
                b"void test_string_hash(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_string_nocase_hash() {
    let mut test1: [::core::ffi::c_char; 15] =
        ::core::mem::transmute::<[u8; 15], [::core::ffi::c_char; 15]>(*b"this is a test\0");
    let mut test2: [::core::ffi::c_char; 15] =
        ::core::mem::transmute::<[u8; 15], [::core::ffi::c_char; 15]>(*b"this is a tesu\0");
    let mut test3: [::core::ffi::c_char; 16] =
        ::core::mem::transmute::<[u8; 16], [::core::ffi::c_char; 16]>(*b"this is a test \0");
    let mut test4: [::core::ffi::c_char; 15] =
        ::core::mem::transmute::<[u8; 15], [::core::ffi::c_char; 15]>(*b"this is a test\0");
    let mut test5: [::core::ffi::c_char; 15] =
        ::core::mem::transmute::<[u8; 15], [::core::ffi::c_char; 15]>(*b"This is a test\0");
    '_c2rust_label: {
        if string_nocase_hash(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) != string_nocase_hash(
            &raw mut test2 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) {
        } else {
            __assert_fail(
                b"string_nocase_hash(test1) != string_nocase_hash(test2)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                117 as ::core::ffi::c_uint,
                b"void test_string_nocase_hash(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if string_nocase_hash(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) != string_nocase_hash(
            &raw mut test3 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) {
        } else {
            __assert_fail(
                b"string_nocase_hash(test1) != string_nocase_hash(test3)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                121 as ::core::ffi::c_uint,
                b"void test_string_nocase_hash(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if string_nocase_hash(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == string_nocase_hash(
            &raw mut test5 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) {
        } else {
            __assert_fail(
                b"string_nocase_hash(test1) == string_nocase_hash(test5)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                125 as ::core::ffi::c_uint,
                b"void test_string_nocase_hash(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if string_nocase_hash(
            &raw mut test1 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) == string_nocase_hash(
            &raw mut test4 as *mut ::core::ffi::c_char as *mut ::core::ffi::c_void,
        ) {
        } else {
            __assert_fail(
                b"string_nocase_hash(test1) == string_nocase_hash(test4)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-functions.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                129 as ::core::ffi::c_uint,
                b"void test_string_nocase_hash(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
static mut tests: [UnitTestFunction; 5] = unsafe {
    [
        Some(test_pointer_hash as unsafe extern "C" fn() -> ()),
        Some(test_int_hash as unsafe extern "C" fn() -> ()),
        Some(test_string_hash as unsafe extern "C" fn() -> ()),
        Some(test_string_nocase_hash as unsafe extern "C" fn() -> ()),
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
