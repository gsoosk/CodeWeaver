extern "C" {
    pub type _SListEntry;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn slist_free(list: *mut SListEntry);
    fn slist_prepend(list: *mut *mut SListEntry, data: SListValue) -> *mut SListEntry;
    fn slist_append(list: *mut *mut SListEntry, data: SListValue) -> *mut SListEntry;
    fn slist_next(listentry: *mut SListEntry) -> *mut SListEntry;
    fn slist_data(listentry: *mut SListEntry) -> SListValue;
    fn slist_nth_entry(list: *mut SListEntry, n: ::core::ffi::c_uint) -> *mut SListEntry;
    fn slist_nth_data(list: *mut SListEntry, n: ::core::ffi::c_uint) -> SListValue;
    fn slist_length(list: *mut SListEntry) -> ::core::ffi::c_uint;
    fn slist_to_array(list: *mut SListEntry) -> *mut SListValue;
    fn slist_remove_entry(list: *mut *mut SListEntry, entry: *mut SListEntry)
        -> ::core::ffi::c_int;
    fn slist_remove_data(
        list: *mut *mut SListEntry,
        callback: SListEqualFunc,
        data: SListValue,
    ) -> ::core::ffi::c_uint;
    fn slist_sort(list: *mut *mut SListEntry, compare_func: SListCompareFunc);
    fn slist_find_data(
        list: *mut SListEntry,
        callback: SListEqualFunc,
        data: SListValue,
    ) -> *mut SListEntry;
    fn slist_iterate(list: *mut *mut SListEntry, iter: *mut SListIterator);
    fn slist_iter_has_more(iterator: *mut SListIterator) -> ::core::ffi::c_int;
    fn slist_iter_next(iterator: *mut SListIterator) -> SListValue;
    fn slist_iter_remove(iterator: *mut SListIterator);
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
pub type SListEntry = _SListEntry;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _SListIterator {
    pub prev_next: *mut *mut SListEntry,
    pub current: *mut SListEntry,
}
pub type SListIterator = _SListIterator;
pub type SListValue = *mut ::core::ffi::c_void;
pub type SListCompareFunc =
    Option<unsafe extern "C" fn(SListValue, SListValue) -> ::core::ffi::c_int>;
pub type SListEqualFunc =
    Option<unsafe extern "C" fn(SListValue, SListValue) -> ::core::ffi::c_int>;
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
pub static mut variable3: ::core::ffi::c_int = 0;
#[no_mangle]
pub static mut variable1: ::core::ffi::c_int = 50 as ::core::ffi::c_int;
#[no_mangle]
pub static mut variable2: ::core::ffi::c_int = 0;
#[no_mangle]
pub static mut variable4: ::core::ffi::c_int = 0;
#[no_mangle]
pub unsafe extern "C" fn generate_list() -> *mut SListEntry {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    '_c2rust_label: {
        if !slist_append(&raw mut list, &raw mut variable1 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable1) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                39 as ::core::ffi::c_uint,
                b"SListEntry *generate_list(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if !slist_append(&raw mut list, &raw mut variable2 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable2) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                40 as ::core::ffi::c_uint,
                b"SListEntry *generate_list(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if !slist_append(&raw mut list, &raw mut variable3 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable3) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                41 as ::core::ffi::c_uint,
                b"SListEntry *generate_list(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if !slist_append(&raw mut list, &raw mut variable4 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable4) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                42 as ::core::ffi::c_uint,
                b"SListEntry *generate_list(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    return list;
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_append() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    '_c2rust_label: {
        if !slist_append(&raw mut list, &raw mut variable1 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable1) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                51 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if !slist_append(&raw mut list, &raw mut variable2 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable2) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                52 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if !slist_append(&raw mut list, &raw mut variable3 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable3) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                53 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if !slist_append(&raw mut list, &raw mut variable4 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable4) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                54 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if slist_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                55 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if slist_nth_data(list, 0 as ::core::ffi::c_uint) == &raw mut variable1 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 0) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                57 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if slist_nth_data(list, 1 as ::core::ffi::c_uint) == &raw mut variable2 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 1) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                58 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if slist_nth_data(list, 2 as ::core::ffi::c_uint) == &raw mut variable3 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 2) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                59 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if slist_nth_data(list, 3 as ::core::ffi::c_uint) == &raw mut variable4 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 3) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                60 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_8: {
        if slist_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                65 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_9: {
        if slist_append(&raw mut list, &raw mut variable1 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_append(&list, &variable1) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                66 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_10: {
        if slist_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                67 as ::core::ffi::c_uint,
                b"void test_slist_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_prepend() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    '_c2rust_label: {
        if !slist_prepend(&raw mut list, &raw mut variable1 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_prepend(&list, &variable1) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                76 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if !slist_prepend(&raw mut list, &raw mut variable2 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_prepend(&list, &variable2) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                77 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if !slist_prepend(&raw mut list, &raw mut variable3 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_prepend(&list, &variable3) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                78 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if !slist_prepend(&raw mut list, &raw mut variable4 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_prepend(&list, &variable4) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                79 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if slist_nth_data(list, 0 as ::core::ffi::c_uint) == &raw mut variable4 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 0) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                81 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if slist_nth_data(list, 1 as ::core::ffi::c_uint) == &raw mut variable3 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 1) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                82 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if slist_nth_data(list, 2 as ::core::ffi::c_uint) == &raw mut variable2 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 2) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                83 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if slist_nth_data(list, 3 as ::core::ffi::c_uint) == &raw mut variable1 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 3) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                84 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_7: {
        if slist_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                89 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if slist_prepend(&raw mut list, &raw mut variable1 as SListValue).is_null() {
        } else {
            __assert_fail(
                b"slist_prepend(&list, &variable1) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                90 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_9: {
        if slist_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                91 as ::core::ffi::c_uint,
                b"void test_slist_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_free() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    list = generate_list();
    slist_free(list);
    slist_free(::core::ptr::null_mut::<SListEntry>());
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_next() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut rover: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    list = generate_list();
    rover = list;
    '_c2rust_label: {
        if slist_data(rover) == &raw mut variable1 as SListValue {
        } else {
            __assert_fail(
                b"slist_data(rover) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                119 as ::core::ffi::c_uint,
                b"void test_slist_next(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rover = slist_next(rover);
    '_c2rust_label_0: {
        if slist_data(rover) == &raw mut variable2 as SListValue {
        } else {
            __assert_fail(
                b"slist_data(rover) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                121 as ::core::ffi::c_uint,
                b"void test_slist_next(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rover = slist_next(rover);
    '_c2rust_label_1: {
        if slist_data(rover) == &raw mut variable3 as SListValue {
        } else {
            __assert_fail(
                b"slist_data(rover) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                123 as ::core::ffi::c_uint,
                b"void test_slist_next(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rover = slist_next(rover);
    '_c2rust_label_2: {
        if slist_data(rover) == &raw mut variable4 as SListValue {
        } else {
            __assert_fail(
                b"slist_data(rover) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                125 as ::core::ffi::c_uint,
                b"void test_slist_next(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rover = slist_next(rover);
    '_c2rust_label_3: {
        if rover.is_null() {
        } else {
            __assert_fail(
                b"rover == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                127 as ::core::ffi::c_uint,
                b"void test_slist_next(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_nth_entry() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut entry: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    list = generate_list();
    entry = slist_nth_entry(list, 0 as ::core::ffi::c_uint);
    '_c2rust_label: {
        if slist_data(entry) == &raw mut variable1 as SListValue {
        } else {
            __assert_fail(
                b"slist_data(entry) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                142 as ::core::ffi::c_uint,
                b"void test_slist_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = slist_nth_entry(list, 1 as ::core::ffi::c_uint);
    '_c2rust_label_0: {
        if slist_data(entry) == &raw mut variable2 as SListValue {
        } else {
            __assert_fail(
                b"slist_data(entry) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                144 as ::core::ffi::c_uint,
                b"void test_slist_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = slist_nth_entry(list, 2 as ::core::ffi::c_uint);
    '_c2rust_label_1: {
        if slist_data(entry) == &raw mut variable3 as SListValue {
        } else {
            __assert_fail(
                b"slist_data(entry) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                146 as ::core::ffi::c_uint,
                b"void test_slist_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = slist_nth_entry(list, 3 as ::core::ffi::c_uint);
    '_c2rust_label_2: {
        if slist_data(entry) == &raw mut variable4 as SListValue {
        } else {
            __assert_fail(
                b"slist_data(entry) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                148 as ::core::ffi::c_uint,
                b"void test_slist_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = slist_nth_entry(list, 4 as ::core::ffi::c_uint);
    '_c2rust_label_3: {
        if entry.is_null() {
        } else {
            __assert_fail(
                b"entry == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                153 as ::core::ffi::c_uint,
                b"void test_slist_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = slist_nth_entry(list, 400 as ::core::ffi::c_uint);
    '_c2rust_label_4: {
        if entry.is_null() {
        } else {
            __assert_fail(
                b"entry == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                155 as ::core::ffi::c_uint,
                b"void test_slist_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_nth_data() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    list = generate_list();
    '_c2rust_label: {
        if slist_nth_data(list, 0 as ::core::ffi::c_uint) == &raw mut variable1 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 0) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                168 as ::core::ffi::c_uint,
                b"void test_slist_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if slist_nth_data(list, 1 as ::core::ffi::c_uint) == &raw mut variable2 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 1) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                169 as ::core::ffi::c_uint,
                b"void test_slist_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if slist_nth_data(list, 2 as ::core::ffi::c_uint) == &raw mut variable3 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 2) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                170 as ::core::ffi::c_uint,
                b"void test_slist_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if slist_nth_data(list, 3 as ::core::ffi::c_uint) == &raw mut variable4 as SListValue {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 3) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                171 as ::core::ffi::c_uint,
                b"void test_slist_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if slist_nth_data(list, 4 as ::core::ffi::c_uint).is_null() {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 4) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                175 as ::core::ffi::c_uint,
                b"void test_slist_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if slist_nth_data(list, 400 as ::core::ffi::c_uint).is_null() {
        } else {
            __assert_fail(
                b"slist_nth_data(list, 400) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                176 as ::core::ffi::c_uint,
                b"void test_slist_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_length() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    list = generate_list();
    '_c2rust_label: {
        if slist_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                189 as ::core::ffi::c_uint,
                b"void test_slist_length(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_prepend(&raw mut list, &raw mut variable1 as SListValue);
    '_c2rust_label_0: {
        if slist_length(list) == 5 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 5\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                195 as ::core::ffi::c_uint,
                b"void test_slist_length(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if slist_length(::core::ptr::null_mut::<SListEntry>()) == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(NULL) == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                199 as ::core::ffi::c_uint,
                b"void test_slist_length(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_remove_entry() {
    let mut empty_list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut entry: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    list = generate_list();
    entry = slist_nth_entry(list, 2 as ::core::ffi::c_uint);
    '_c2rust_label: {
        if slist_remove_entry(&raw mut list, entry) != 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"slist_remove_entry(&list, entry) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                215 as ::core::ffi::c_uint,
                b"void test_slist_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if slist_length(list) == 3 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 3\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                216 as ::core::ffi::c_uint,
                b"void test_slist_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = slist_nth_entry(list, 0 as ::core::ffi::c_uint);
    '_c2rust_label_1: {
        if slist_remove_entry(&raw mut list, entry) != 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"slist_remove_entry(&list, entry) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                221 as ::core::ffi::c_uint,
                b"void test_slist_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if slist_length(list) == 2 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 2\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                222 as ::core::ffi::c_uint,
                b"void test_slist_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if slist_remove_entry(&raw mut list, entry) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"slist_remove_entry(&list, entry) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                228 as ::core::ffi::c_uint,
                b"void test_slist_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if slist_remove_entry(&raw mut list, ::core::ptr::null_mut::<SListEntry>())
            == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"slist_remove_entry(&list, NULL) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                232 as ::core::ffi::c_uint,
                b"void test_slist_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if slist_remove_entry(&raw mut empty_list, ::core::ptr::null_mut::<SListEntry>())
            == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"slist_remove_entry(&empty_list, NULL) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                236 as ::core::ffi::c_uint,
                b"void test_slist_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_remove_data() {
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
    let mut num_entries: ::core::ffi::c_uint = (::core::mem::size_of::<[::core::ffi::c_int; 13]>()
        as usize)
        .wrapping_div(::core::mem::size_of::<::core::ffi::c_int>() as usize)
        as ::core::ffi::c_uint;
    let mut val: ::core::ffi::c_int = 0;
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut i: ::core::ffi::c_uint = 0;
    list = ::core::ptr::null_mut::<SListEntry>();
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        slist_prepend(
            &raw mut list,
            (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SListValue,
        );
        i = i.wrapping_add(1);
    }
    val = 0 as ::core::ffi::c_int;
    '_c2rust_label: {
        if slist_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as SListValue,
        ) == 0 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"slist_remove_data(&list, int_equal, &val) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                260 as ::core::ffi::c_uint,
                b"void test_slist_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    val = 56 as ::core::ffi::c_int;
    '_c2rust_label_0: {
        if slist_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as SListValue,
        ) == 0 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"slist_remove_data(&list, int_equal, &val) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                262 as ::core::ffi::c_uint,
                b"void test_slist_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    val = 8 as ::core::ffi::c_int;
    '_c2rust_label_1: {
        if slist_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as SListValue,
        ) == 1 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"slist_remove_data(&list, int_equal, &val) == 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                267 as ::core::ffi::c_uint,
                b"void test_slist_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if slist_length(list) == num_entries.wrapping_sub(1 as ::core::ffi::c_uint) {
        } else {
            __assert_fail(
                b"slist_length(list) == num_entries - 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                268 as ::core::ffi::c_uint,
                b"void test_slist_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    val = 4 as ::core::ffi::c_int;
    '_c2rust_label_3: {
        if slist_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as SListValue,
        ) == 4 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"slist_remove_data(&list, int_equal, &val) == 4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                273 as ::core::ffi::c_uint,
                b"void test_slist_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if slist_length(list) == num_entries.wrapping_sub(5 as ::core::ffi::c_uint) {
        } else {
            __assert_fail(
                b"slist_length(list) == num_entries - 5\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                274 as ::core::ffi::c_uint,
                b"void test_slist_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    val = 89 as ::core::ffi::c_int;
    '_c2rust_label_5: {
        if slist_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as SListValue,
        ) == 1 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"slist_remove_data(&list, int_equal, &val) == 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                279 as ::core::ffi::c_uint,
                b"void test_slist_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if slist_length(list) == num_entries.wrapping_sub(6 as ::core::ffi::c_uint) {
        } else {
            __assert_fail(
                b"slist_length(list) == num_entries - 6\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                280 as ::core::ffi::c_uint,
                b"void test_slist_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_sort() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
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
    list = ::core::ptr::null_mut::<SListEntry>();
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        slist_prepend(
            &raw mut list,
            (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SListValue,
        );
        i = i.wrapping_add(1);
    }
    slist_sort(
        &raw mut list,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label: {
        if slist_length(list) == num_entries {
        } else {
            __assert_fail(
                b"slist_length(list) == num_entries\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                303 as ::core::ffi::c_uint,
                b"void test_slist_sort(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
        value = slist_nth_data(list, i) as *mut ::core::ffi::c_int;
        '_c2rust_label_0: {
            if *value == sorted[i as usize] {
            } else {
                __assert_fail(
                    b"*value == sorted[i]\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    311 as ::core::ffi::c_uint,
                    b"void test_slist_sort(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    slist_free(list);
    list = ::core::ptr::null_mut::<SListEntry>();
    slist_sort(
        &raw mut list,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_1: {
        if list.is_null() {
        } else {
            __assert_fail(
                b"list == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                322 as ::core::ffi::c_uint,
                b"void test_slist_sort(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_find_data() {
    let mut entries: [::core::ffi::c_int; 10] = [
        89 as ::core::ffi::c_int,
        23 as ::core::ffi::c_int,
        42 as ::core::ffi::c_int,
        16 as ::core::ffi::c_int,
        15 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        99 as ::core::ffi::c_int,
        50 as ::core::ffi::c_int,
        30 as ::core::ffi::c_int,
    ];
    let mut num_entries: ::core::ffi::c_int = (::core::mem::size_of::<[::core::ffi::c_int; 10]>()
        as usize)
        .wrapping_div(::core::mem::size_of::<::core::ffi::c_int>() as usize)
        as ::core::ffi::c_int;
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut result: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut i: ::core::ffi::c_int = 0;
    let mut val: ::core::ffi::c_int = 0;
    let mut data: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    list = ::core::ptr::null_mut::<SListEntry>();
    i = 0 as ::core::ffi::c_int;
    while i < num_entries {
        slist_append(
            &raw mut list,
            (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SListValue,
        );
        i += 1;
    }
    i = 0 as ::core::ffi::c_int;
    while i < num_entries {
        val = entries[i as usize];
        result = slist_find_data(
            list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as SListValue,
        );
        '_c2rust_label: {
            if !result.is_null() {
            } else {
                __assert_fail(
                    b"result != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    350 as ::core::ffi::c_uint,
                    b"void test_slist_find_data(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        data = slist_data(result) as *mut ::core::ffi::c_int;
        '_c2rust_label_0: {
            if *data == val {
            } else {
                __assert_fail(
                    b"*data == val\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    353 as ::core::ffi::c_uint,
                    b"void test_slist_find_data(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    val = 0 as ::core::ffi::c_int;
    '_c2rust_label_1: {
        if slist_find_data(
            list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as SListValue,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"slist_find_data(list, int_equal, &val) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                359 as ::core::ffi::c_uint,
                b"void test_slist_find_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    val = 56 as ::core::ffi::c_int;
    '_c2rust_label_2: {
        if slist_find_data(
            list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as SListValue,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"slist_find_data(list, int_equal, &val) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                361 as ::core::ffi::c_uint,
                b"void test_slist_find_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_to_array() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut array: *mut *mut ::core::ffi::c_void =
        ::core::ptr::null_mut::<*mut ::core::ffi::c_void>();
    list = generate_list();
    array = slist_to_array(list) as *mut *mut ::core::ffi::c_void;
    '_c2rust_label: {
        if *array.offset(0 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as *mut ::core::ffi::c_void
        {
        } else {
            __assert_fail(
                b"array[0] == &variable1\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                375 as ::core::ffi::c_uint,
                b"void test_slist_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if *array.offset(1 as ::core::ffi::c_int as isize)
            == &raw mut variable2 as *mut ::core::ffi::c_void
        {
        } else {
            __assert_fail(
                b"array[1] == &variable2\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                376 as ::core::ffi::c_uint,
                b"void test_slist_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if *array.offset(2 as ::core::ffi::c_int as isize)
            == &raw mut variable3 as *mut ::core::ffi::c_void
        {
        } else {
            __assert_fail(
                b"array[2] == &variable3\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                377 as ::core::ffi::c_uint,
                b"void test_slist_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if *array.offset(3 as ::core::ffi::c_int as isize)
            == &raw mut variable4 as *mut ::core::ffi::c_void
        {
        } else {
            __assert_fail(
                b"array[3] == &variable4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                378 as ::core::ffi::c_uint,
                b"void test_slist_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_free(array as *mut ::core::ffi::c_void);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    array = slist_to_array(list) as *mut *mut ::core::ffi::c_void;
    '_c2rust_label_3: {
        if array.is_null() {
        } else {
            __assert_fail(
                b"array == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                387 as ::core::ffi::c_uint,
                b"void test_slist_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_iterate() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut iter: SListIterator = _SListIterator {
        prev_next: ::core::ptr::null_mut::<*mut SListEntry>(),
        current: ::core::ptr::null_mut::<SListEntry>(),
    };
    let mut data: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut a: ::core::ffi::c_int = 0;
    let mut i: ::core::ffi::c_int = 0;
    let mut counter: ::core::ffi::c_int = 0;
    list = ::core::ptr::null_mut::<SListEntry>();
    i = 0 as ::core::ffi::c_int;
    while i < 50 as ::core::ffi::c_int {
        slist_prepend(&raw mut list, &raw mut a as SListValue);
        i += 1;
    }
    counter = 0 as ::core::ffi::c_int;
    slist_iterate(&raw mut list, &raw mut iter);
    slist_iter_remove(&raw mut iter);
    while slist_iter_has_more(&raw mut iter) != 0 {
        data = slist_iter_next(&raw mut iter) as *mut ::core::ffi::c_int;
        counter += 1;
        if counter % 2 as ::core::ffi::c_int == 0 as ::core::ffi::c_int {
            slist_iter_remove(&raw mut iter);
            slist_iter_remove(&raw mut iter);
        }
    }
    '_c2rust_label: {
        if slist_iter_next(&raw mut iter).is_null() {
        } else {
            __assert_fail(
                b"slist_iter_next(&iter) == SLIST_NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                440 as ::core::ffi::c_uint,
                b"void test_slist_iterate(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_iter_remove(&raw mut iter);
    '_c2rust_label_0: {
        if counter == 50 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"counter == 50\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                446 as ::core::ffi::c_uint,
                b"void test_slist_iterate(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if slist_length(list) == 25 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"slist_length(list) == 25\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                447 as ::core::ffi::c_uint,
                b"void test_slist_iterate(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    slist_free(list);
    list = ::core::ptr::null_mut::<SListEntry>();
    counter = 0 as ::core::ffi::c_int;
    slist_iterate(&raw mut list, &raw mut iter);
    while slist_iter_has_more(&raw mut iter) != 0 {
        data = slist_iter_next(&raw mut iter) as *mut ::core::ffi::c_int;
        counter += 1;
        if counter % 2 as ::core::ffi::c_int == 0 as ::core::ffi::c_int {
            slist_iter_remove(&raw mut iter);
        }
    }
    '_c2rust_label_2: {
        if counter == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"counter == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                471 as ::core::ffi::c_uint,
                b"void test_slist_iterate(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_slist_iterate_bad_remove() {
    let mut list: *mut SListEntry = ::core::ptr::null_mut::<SListEntry>();
    let mut iter: SListIterator = _SListIterator {
        prev_next: ::core::ptr::null_mut::<*mut SListEntry>(),
        current: ::core::ptr::null_mut::<SListEntry>(),
    };
    let mut values: [::core::ffi::c_int; 49] = [0; 49];
    let mut i: ::core::ffi::c_int = 0;
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    list = ::core::ptr::null_mut::<SListEntry>();
    i = 0 as ::core::ffi::c_int;
    while i < 49 as ::core::ffi::c_int {
        values[i as usize] = i;
        slist_prepend(
            &raw mut list,
            (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SListValue,
        );
        i += 1;
    }
    slist_iterate(&raw mut list, &raw mut iter);
    while slist_iter_has_more(&raw mut iter) != 0 {
        val = slist_iter_next(&raw mut iter) as *mut ::core::ffi::c_int;
        if *val % 2 as ::core::ffi::c_int == 0 as ::core::ffi::c_int {
            '_c2rust_label: {
                if slist_remove_data(
                    &raw mut list,
                    Some(
                        int_equal
                            as unsafe extern "C" fn(
                                *mut ::core::ffi::c_void,
                                *mut ::core::ffi::c_void,
                            )
                                -> ::core::ffi::c_int,
                    ),
                    val as SListValue,
                ) != 0 as ::core::ffi::c_uint
                {
                } else {
                    __assert_fail(
                        b"slist_remove_data(&list, int_equal, val) != 0\0" as *const u8
                            as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-slist.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        508 as ::core::ffi::c_uint,
                        b"void test_slist_iterate_bad_remove(void)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
            slist_iter_remove(&raw mut iter);
        }
    }
    slist_free(list);
}
static mut tests: [UnitTestFunction; 15] = unsafe {
    [
        Some(test_slist_append as unsafe extern "C" fn() -> ()),
        Some(test_slist_prepend as unsafe extern "C" fn() -> ()),
        Some(test_slist_free as unsafe extern "C" fn() -> ()),
        Some(test_slist_next as unsafe extern "C" fn() -> ()),
        Some(test_slist_nth_entry as unsafe extern "C" fn() -> ()),
        Some(test_slist_nth_data as unsafe extern "C" fn() -> ()),
        Some(test_slist_length as unsafe extern "C" fn() -> ()),
        Some(test_slist_remove_entry as unsafe extern "C" fn() -> ()),
        Some(test_slist_remove_data as unsafe extern "C" fn() -> ()),
        Some(test_slist_sort as unsafe extern "C" fn() -> ()),
        Some(test_slist_find_data as unsafe extern "C" fn() -> ()),
        Some(test_slist_to_array as unsafe extern "C" fn() -> ()),
        Some(test_slist_iterate as unsafe extern "C" fn() -> ()),
        Some(test_slist_iterate_bad_remove as unsafe extern "C" fn() -> ()),
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
