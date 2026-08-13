extern "C" {
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn arraylist_new(length: ::core::ffi::c_uint) -> *mut ArrayList;
    fn arraylist_free(arraylist: *mut ArrayList);
    fn arraylist_append(arraylist: *mut ArrayList, data: ArrayListValue) -> ::core::ffi::c_int;
    fn arraylist_prepend(arraylist: *mut ArrayList, data: ArrayListValue) -> ::core::ffi::c_int;
    fn arraylist_remove(arraylist: *mut ArrayList, index: ::core::ffi::c_uint);
    fn arraylist_remove_range(
        arraylist: *mut ArrayList,
        index: ::core::ffi::c_uint,
        length: ::core::ffi::c_uint,
    );
    fn arraylist_insert(
        arraylist: *mut ArrayList,
        index: ::core::ffi::c_uint,
        data: ArrayListValue,
    ) -> ::core::ffi::c_int;
    fn arraylist_index_of(
        arraylist: *mut ArrayList,
        callback: ArrayListEqualFunc,
        data: ArrayListValue,
    ) -> ::core::ffi::c_int;
    fn arraylist_clear(arraylist: *mut ArrayList);
    fn arraylist_sort(arraylist: *mut ArrayList, compare_func: ArrayListCompareFunc);
    fn int_equal(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn int_compare(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
}
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type ArrayListValue = *mut ::core::ffi::c_void;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _ArrayList {
    pub data: *mut ArrayListValue,
    pub length: ::core::ffi::c_uint,
    pub _alloced: ::core::ffi::c_uint,
}
pub type ArrayList = _ArrayList;
pub type ArrayListEqualFunc =
    Option<unsafe extern "C" fn(ArrayListValue, ArrayListValue) -> ::core::ffi::c_int>;
pub type ArrayListCompareFunc =
    Option<unsafe extern "C" fn(ArrayListValue, ArrayListValue) -> ::core::ffi::c_int>;
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
pub static mut variable1: ::core::ffi::c_int = 0;
#[no_mangle]
pub static mut variable2: ::core::ffi::c_int = 0;
#[no_mangle]
pub static mut variable3: ::core::ffi::c_int = 0;
#[no_mangle]
pub static mut variable4: ::core::ffi::c_int = 0;
#[no_mangle]
pub unsafe extern "C" fn generate_arraylist() -> *mut ArrayList {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    let mut i: ::core::ffi::c_int = 0;
    arraylist = arraylist_new(0 as ::core::ffi::c_uint);
    i = 0 as ::core::ffi::c_int;
    while i < 4 as ::core::ffi::c_int {
        arraylist_append(arraylist, &raw mut variable1 as ArrayListValue);
        arraylist_append(arraylist, &raw mut variable2 as ArrayListValue);
        arraylist_append(arraylist, &raw mut variable3 as ArrayListValue);
        arraylist_append(arraylist, &raw mut variable4 as ArrayListValue);
        i += 1;
    }
    return arraylist;
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_new_free() {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    arraylist = arraylist_new(0 as ::core::ffi::c_uint);
    '_c2rust_label: {
        if !arraylist.is_null() {
        } else {
            __assert_fail(
                b"arraylist != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                59 as ::core::ffi::c_uint,
                b"void test_arraylist_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
    arraylist = arraylist_new(10 as ::core::ffi::c_uint);
    '_c2rust_label_0: {
        if !arraylist.is_null() {
        } else {
            __assert_fail(
                b"arraylist != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                65 as ::core::ffi::c_uint,
                b"void test_arraylist_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
    arraylist_free(::core::ptr::null_mut::<ArrayList>());
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    arraylist = arraylist_new(0 as ::core::ffi::c_uint);
    '_c2rust_label_1: {
        if arraylist.is_null() {
        } else {
            __assert_fail(
                b"arraylist == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                76 as ::core::ffi::c_uint,
                b"void test_arraylist_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(1 as ::core::ffi::c_int);
    arraylist = arraylist_new(100 as ::core::ffi::c_uint);
    '_c2rust_label_2: {
        if arraylist.is_null() {
        } else {
            __assert_fail(
                b"arraylist == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                80 as ::core::ffi::c_uint,
                b"void test_arraylist_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_append() {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    let mut i: ::core::ffi::c_int = 0;
    arraylist = arraylist_new(0 as ::core::ffi::c_uint);
    '_c2rust_label: {
        if (*arraylist).length == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                90 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if arraylist_append(arraylist, &raw mut variable1 as ArrayListValue)
            != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_append(arraylist, &variable1) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                94 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if (*arraylist).length == 1 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 1\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                95 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if arraylist_append(arraylist, &raw mut variable2 as ArrayListValue)
            != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_append(arraylist, &variable2) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                97 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if (*arraylist).length == 2 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 2\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                98 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if arraylist_append(arraylist, &raw mut variable3 as ArrayListValue)
            != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_append(arraylist, &variable3) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                100 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if (*arraylist).length == 3 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 3\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                101 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if arraylist_append(arraylist, &raw mut variable4 as ArrayListValue)
            != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_append(arraylist, &variable4) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                103 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if (*arraylist).length == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                104 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if *(*arraylist).data.offset(0 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[0] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                106 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_9: {
        if *(*arraylist).data.offset(1 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[1] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                107 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_10: {
        if *(*arraylist).data.offset(2 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[2] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                108 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_11: {
        if *(*arraylist).data.offset(3 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[3] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                109 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < 10000 as ::core::ffi::c_int {
        '_c2rust_label_12: {
            if arraylist_append(arraylist, ::core::ptr::null_mut::<::core::ffi::c_void>())
                != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"arraylist_append(arraylist, NULL) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    114 as ::core::ffi::c_uint,
                    b"void test_arraylist_append(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    arraylist_free(arraylist);
    arraylist = arraylist_new(100 as ::core::ffi::c_uint);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    i = 0 as ::core::ffi::c_int;
    while i < 100 as ::core::ffi::c_int {
        '_c2rust_label_13: {
            if arraylist_append(arraylist, ::core::ptr::null_mut::<::core::ffi::c_void>())
                != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"arraylist_append(arraylist, NULL) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    126 as ::core::ffi::c_uint,
                    b"void test_arraylist_append(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    '_c2rust_label_14: {
        if (*arraylist).length == 100 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 100\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                129 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_15: {
        if arraylist_append(arraylist, ::core::ptr::null_mut::<::core::ffi::c_void>())
            == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_append(arraylist, NULL) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                130 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_16: {
        if (*arraylist).length == 100 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 100\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                131 as ::core::ffi::c_uint,
                b"void test_arraylist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_prepend() {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    let mut i: ::core::ffi::c_int = 0;
    arraylist = arraylist_new(0 as ::core::ffi::c_uint);
    '_c2rust_label: {
        if (*arraylist).length == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                144 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if arraylist_prepend(arraylist, &raw mut variable1 as ArrayListValue)
            != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_prepend(arraylist, &variable1) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                148 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if (*arraylist).length == 1 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 1\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                149 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if arraylist_prepend(arraylist, &raw mut variable2 as ArrayListValue)
            != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_prepend(arraylist, &variable2) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                151 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if (*arraylist).length == 2 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 2\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                152 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if arraylist_prepend(arraylist, &raw mut variable3 as ArrayListValue)
            != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_prepend(arraylist, &variable3) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                154 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if (*arraylist).length == 3 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 3\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                155 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if arraylist_prepend(arraylist, &raw mut variable4 as ArrayListValue)
            != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_prepend(arraylist, &variable4) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                157 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if (*arraylist).length == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                158 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if *(*arraylist).data.offset(0 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[0] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                160 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_9: {
        if *(*arraylist).data.offset(1 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[1] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                161 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_10: {
        if *(*arraylist).data.offset(2 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[2] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                162 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_11: {
        if *(*arraylist).data.offset(3 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[3] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                163 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < 10000 as ::core::ffi::c_int {
        '_c2rust_label_12: {
            if arraylist_prepend(arraylist, ::core::ptr::null_mut::<::core::ffi::c_void>())
                != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"arraylist_prepend(arraylist, NULL) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    168 as ::core::ffi::c_uint,
                    b"void test_arraylist_prepend(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    arraylist_free(arraylist);
    arraylist = arraylist_new(100 as ::core::ffi::c_uint);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    i = 0 as ::core::ffi::c_int;
    while i < 100 as ::core::ffi::c_int {
        '_c2rust_label_13: {
            if arraylist_prepend(arraylist, ::core::ptr::null_mut::<::core::ffi::c_void>())
                != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"arraylist_prepend(arraylist, NULL) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    180 as ::core::ffi::c_uint,
                    b"void test_arraylist_prepend(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    '_c2rust_label_14: {
        if (*arraylist).length == 100 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 100\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                183 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_15: {
        if arraylist_prepend(arraylist, ::core::ptr::null_mut::<::core::ffi::c_void>())
            == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_prepend(arraylist, NULL) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                184 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_16: {
        if (*arraylist).length == 100 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 100\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                185 as ::core::ffi::c_uint,
                b"void test_arraylist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_insert() {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    let mut i: ::core::ffi::c_int = 0;
    arraylist = generate_arraylist();
    '_c2rust_label: {
        if (*arraylist).length == 16 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 16\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                199 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if arraylist_insert(
            arraylist,
            17 as ::core::ffi::c_uint,
            &raw mut variable1 as ArrayListValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_insert(arraylist, 17, &variable1) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                200 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if (*arraylist).length == 16 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 16\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                201 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if (*arraylist).length == 16 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 16\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                205 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if *(*arraylist).data.offset(4 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[4] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                206 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if *(*arraylist).data.offset(5 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[5] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                207 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if *(*arraylist).data.offset(6 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[6] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                208 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if arraylist_insert(
            arraylist,
            5 as ::core::ffi::c_uint,
            &raw mut variable4 as ArrayListValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_insert(arraylist, 5, &variable4) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                210 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if (*arraylist).length == 17 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 17\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                212 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if *(*arraylist).data.offset(4 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[4] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                213 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_9: {
        if *(*arraylist).data.offset(5 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[5] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                214 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_10: {
        if *(*arraylist).data.offset(6 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[6] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                215 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_11: {
        if *(*arraylist).data.offset(7 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[7] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                216 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_12: {
        if *(*arraylist).data.offset(0 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[0] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                220 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_13: {
        if *(*arraylist).data.offset(1 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[1] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                221 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_14: {
        if *(*arraylist).data.offset(2 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[2] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                222 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_15: {
        if arraylist_insert(
            arraylist,
            0 as ::core::ffi::c_uint,
            &raw mut variable4 as ArrayListValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_insert(arraylist, 0, &variable4) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                224 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_16: {
        if (*arraylist).length == 18 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 18\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                226 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_17: {
        if *(*arraylist).data.offset(0 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[0] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                227 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_18: {
        if *(*arraylist).data.offset(1 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[1] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                228 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_19: {
        if *(*arraylist).data.offset(2 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[2] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                229 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_20: {
        if *(*arraylist).data.offset(3 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[3] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                230 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_21: {
        if *(*arraylist).data.offset(15 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[15] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                234 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_22: {
        if *(*arraylist).data.offset(16 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[16] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                235 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_23: {
        if *(*arraylist).data.offset(17 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[17] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                236 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_24: {
        if arraylist_insert(
            arraylist,
            18 as ::core::ffi::c_uint,
            &raw mut variable1 as ArrayListValue,
        ) != 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_insert(arraylist, 18, &variable1) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                238 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_25: {
        if (*arraylist).length == 19 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 19\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                240 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_26: {
        if *(*arraylist).data.offset(15 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[15] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                241 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_27: {
        if *(*arraylist).data.offset(16 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[16] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                242 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_28: {
        if *(*arraylist).data.offset(17 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[17] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                243 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_29: {
        if *(*arraylist).data.offset(18 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[18] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                244 as ::core::ffi::c_uint,
                b"void test_arraylist_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < 10000 as ::core::ffi::c_int {
        arraylist_insert(
            arraylist,
            10 as ::core::ffi::c_uint,
            &raw mut variable1 as ArrayListValue,
        );
        i += 1;
    }
    arraylist_free(arraylist);
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_remove_range() {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    arraylist = generate_arraylist();
    '_c2rust_label: {
        if (*arraylist).length == 16 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 16\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                261 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if *(*arraylist).data.offset(3 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[3] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                262 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if *(*arraylist).data.offset(4 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[4] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                263 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if *(*arraylist).data.offset(5 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[5] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                264 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if *(*arraylist).data.offset(6 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[6] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                265 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_remove_range(
        arraylist,
        4 as ::core::ffi::c_uint,
        3 as ::core::ffi::c_uint,
    );
    '_c2rust_label_4: {
        if (*arraylist).length == 13 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 13\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                269 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if *(*arraylist).data.offset(3 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[3] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                270 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if *(*arraylist).data.offset(4 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[4] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                271 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if *(*arraylist).data.offset(5 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[5] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                272 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if *(*arraylist).data.offset(6 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[6] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                273 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_remove_range(
        arraylist,
        10 as ::core::ffi::c_uint,
        10 as ::core::ffi::c_uint,
    );
    arraylist_remove_range(
        arraylist,
        0 as ::core::ffi::c_uint,
        16 as ::core::ffi::c_uint,
    );
    '_c2rust_label_9: {
        if (*arraylist).length == 13 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 13\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                280 as ::core::ffi::c_uint,
                b"void test_arraylist_remove_range(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_remove() {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    arraylist = generate_arraylist();
    '_c2rust_label: {
        if (*arraylist).length == 16 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 16\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                291 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if *(*arraylist).data.offset(3 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[3] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                292 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if *(*arraylist).data.offset(4 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[4] == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                293 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if *(*arraylist).data.offset(5 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[5] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                294 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if *(*arraylist).data.offset(6 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[6] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                295 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_remove(arraylist, 4 as ::core::ffi::c_uint);
    '_c2rust_label_4: {
        if (*arraylist).length == 15 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 15\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                299 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if *(*arraylist).data.offset(3 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[3] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                300 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if *(*arraylist).data.offset(4 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[4] == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                301 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if *(*arraylist).data.offset(5 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[5] == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                302 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if *(*arraylist).data.offset(6 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[6] == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                303 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_remove(arraylist, 15 as ::core::ffi::c_uint);
    '_c2rust_label_9: {
        if (*arraylist).length == 15 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 15\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                309 as ::core::ffi::c_uint,
                b"void test_arraylist_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_index_of() {
    let mut entries: [::core::ffi::c_int; 10] = [
        89 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        23 as ::core::ffi::c_int,
        42 as ::core::ffi::c_int,
        16 as ::core::ffi::c_int,
        15 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        99 as ::core::ffi::c_int,
        50 as ::core::ffi::c_int,
        30 as ::core::ffi::c_int,
    ];
    let mut num_entries: ::core::ffi::c_int = 0;
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    let mut i: ::core::ffi::c_int = 0;
    let mut index: ::core::ffi::c_int = 0;
    let mut val: ::core::ffi::c_int = 0;
    num_entries = (::core::mem::size_of::<[::core::ffi::c_int; 10]>() as usize)
        .wrapping_div(::core::mem::size_of::<::core::ffi::c_int>() as usize)
        as ::core::ffi::c_int;
    arraylist = arraylist_new(0 as ::core::ffi::c_uint);
    i = 0 as ::core::ffi::c_int;
    while i < num_entries {
        arraylist_append(
            arraylist,
            (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as ArrayListValue,
        );
        i += 1;
    }
    i = 0 as ::core::ffi::c_int;
    while i < num_entries {
        val = entries[i as usize];
        index = arraylist_index_of(
            arraylist,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ArrayListValue,
        );
        '_c2rust_label: {
            if index == i {
            } else {
                __assert_fail(
                    b"index == i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    340 as ::core::ffi::c_uint,
                    b"void test_arraylist_index_of(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    val = 0 as ::core::ffi::c_int;
    '_c2rust_label_0: {
        if arraylist_index_of(
            arraylist,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ArrayListValue,
        ) < 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_index_of(arraylist, int_equal, &val) < 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                346 as ::core::ffi::c_uint,
                b"void test_arraylist_index_of(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    val = 57 as ::core::ffi::c_int;
    '_c2rust_label_1: {
        if arraylist_index_of(
            arraylist,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ArrayListValue,
        ) < 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"arraylist_index_of(arraylist, int_equal, &val) < 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                348 as ::core::ffi::c_uint,
                b"void test_arraylist_index_of(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_clear() {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    arraylist = arraylist_new(0 as ::core::ffi::c_uint);
    arraylist_clear(arraylist);
    '_c2rust_label: {
        if (*arraylist).length == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                362 as ::core::ffi::c_uint,
                b"void test_arraylist_clear(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_append(arraylist, &raw mut variable1 as ArrayListValue);
    arraylist_append(arraylist, &raw mut variable2 as ArrayListValue);
    arraylist_append(arraylist, &raw mut variable3 as ArrayListValue);
    arraylist_append(arraylist, &raw mut variable4 as ArrayListValue);
    arraylist_clear(arraylist);
    '_c2rust_label_0: {
        if (*arraylist).length == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                373 as ::core::ffi::c_uint,
                b"void test_arraylist_clear(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
}
#[no_mangle]
pub unsafe extern "C" fn test_arraylist_sort() {
    let mut arraylist: *mut ArrayList = ::core::ptr::null_mut::<ArrayList>();
    let mut entries: [::core::ffi::c_int; 13] = [
        89 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        23 as ::core::ffi::c_int,
        42 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        16 as ::core::ffi::c_int,
        15 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        99 as ::core::ffi::c_int,
        50 as ::core::ffi::c_int,
        30 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
    ];
    let mut sorted: [::core::ffi::c_int; 13] = [
        4 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        15 as ::core::ffi::c_int,
        16 as ::core::ffi::c_int,
        23 as ::core::ffi::c_int,
        30 as ::core::ffi::c_int,
        42 as ::core::ffi::c_int,
        50 as ::core::ffi::c_int,
        89 as ::core::ffi::c_int,
        99 as ::core::ffi::c_int,
    ];
    let mut num_entries: ::core::ffi::c_uint = (::core::mem::size_of::<[::core::ffi::c_int; 13]>()
        as usize)
        .wrapping_div(::core::mem::size_of::<::core::ffi::c_int>() as usize)
        as ::core::ffi::c_uint;
    let mut i: ::core::ffi::c_uint = 0;
    arraylist = arraylist_new(10 as ::core::ffi::c_uint);
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        arraylist_prepend(
            arraylist,
            (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as ArrayListValue,
        );
        i = i.wrapping_add(1);
    }
    arraylist_sort(
        arraylist,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label: {
        if (*arraylist).length == num_entries {
        } else {
            __assert_fail(
                b"arraylist->length == num_entries\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                396 as ::core::ffi::c_uint,
                b"void test_arraylist_sort(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
        value = *(*arraylist).data.offset(i as isize) as *mut ::core::ffi::c_int;
        '_c2rust_label_0: {
            if *value == sorted[i as usize] {
            } else {
                __assert_fail(
                    b"*value == sorted[i]\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    404 as ::core::ffi::c_uint,
                    b"void test_arraylist_sort(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    arraylist_free(arraylist);
    arraylist = arraylist_new(5 as ::core::ffi::c_uint);
    arraylist_sort(
        arraylist,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_1: {
        if (*arraylist).length == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                415 as ::core::ffi::c_uint,
                b"void test_arraylist_sort(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
    arraylist = arraylist_new(5 as ::core::ffi::c_uint);
    arraylist_prepend(
        arraylist,
        (&raw mut entries as *mut ::core::ffi::c_int).offset(0 as ::core::ffi::c_int as isize)
            as *mut ::core::ffi::c_int as ArrayListValue,
    );
    arraylist_sort(
        arraylist,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_2: {
        if (*arraylist).length == 1 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"arraylist->length == 1\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                426 as ::core::ffi::c_uint,
                b"void test_arraylist_sort(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if *(*arraylist).data.offset(0 as ::core::ffi::c_int as isize)
            == (&raw mut entries as *mut ::core::ffi::c_int)
                .offset(0 as ::core::ffi::c_int as isize) as *mut ::core::ffi::c_int
                as ArrayListValue
        {
        } else {
            __assert_fail(
                b"arraylist->data[0] == &entries[0]\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-arraylist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                427 as ::core::ffi::c_uint,
                b"void test_arraylist_sort(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    arraylist_free(arraylist);
}
static mut tests: [UnitTestFunction; 10] = unsafe {
    [
        Some(test_arraylist_new_free as unsafe extern "C" fn() -> ()),
        Some(test_arraylist_append as unsafe extern "C" fn() -> ()),
        Some(test_arraylist_prepend as unsafe extern "C" fn() -> ()),
        Some(test_arraylist_insert as unsafe extern "C" fn() -> ()),
        Some(test_arraylist_remove as unsafe extern "C" fn() -> ()),
        Some(test_arraylist_remove_range as unsafe extern "C" fn() -> ()),
        Some(test_arraylist_index_of as unsafe extern "C" fn() -> ()),
        Some(test_arraylist_clear as unsafe extern "C" fn() -> ()),
        Some(test_arraylist_sort as unsafe extern "C" fn() -> ()),
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
