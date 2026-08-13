extern "C" {
    pub type _ListEntry;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn list_free(list: *mut ListEntry);
    fn list_prepend(list: *mut *mut ListEntry, data: ListValue) -> *mut ListEntry;
    fn list_append(list: *mut *mut ListEntry, data: ListValue) -> *mut ListEntry;
    fn list_prev(listentry: *mut ListEntry) -> *mut ListEntry;
    fn list_next(listentry: *mut ListEntry) -> *mut ListEntry;
    fn list_data(listentry: *mut ListEntry) -> ListValue;
    fn list_nth_entry(list: *mut ListEntry, n: ::core::ffi::c_uint) -> *mut ListEntry;
    fn list_nth_data(list: *mut ListEntry, n: ::core::ffi::c_uint) -> ListValue;
    fn list_length(list: *mut ListEntry) -> ::core::ffi::c_uint;
    fn list_to_array(list: *mut ListEntry) -> *mut ListValue;
    fn list_remove_entry(list: *mut *mut ListEntry, entry: *mut ListEntry) -> ::core::ffi::c_int;
    fn list_remove_data(
        list: *mut *mut ListEntry,
        callback: ListEqualFunc,
        data: ListValue,
    ) -> ::core::ffi::c_uint;
    fn list_sort(list: *mut *mut ListEntry, compare_func: ListCompareFunc);
    fn list_find_data(
        list: *mut ListEntry,
        callback: ListEqualFunc,
        data: ListValue,
    ) -> *mut ListEntry;
    fn list_iterate(list: *mut *mut ListEntry, iter: *mut ListIterator);
    fn list_iter_has_more(iterator: *mut ListIterator) -> ::core::ffi::c_int;
    fn list_iter_next(iterator: *mut ListIterator) -> ListValue;
    fn list_iter_remove(iterator: *mut ListIterator);
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
pub type ListEntry = _ListEntry;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _ListIterator {
    pub prev_next: *mut *mut ListEntry,
    pub current: *mut ListEntry,
}
pub type ListIterator = _ListIterator;
pub type ListValue = *mut ::core::ffi::c_void;
pub type ListCompareFunc = Option<unsafe extern "C" fn(ListValue, ListValue) -> ::core::ffi::c_int>;
pub type ListEqualFunc = Option<unsafe extern "C" fn(ListValue, ListValue) -> ::core::ffi::c_int>;
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
pub static mut variable2: ::core::ffi::c_int = 0;
#[no_mangle]
pub static mut variable1: ::core::ffi::c_int = 50 as ::core::ffi::c_int;
#[no_mangle]
pub static mut variable4: ::core::ffi::c_int = 0;
#[no_mangle]
pub unsafe extern "C" fn generate_list() -> *mut ListEntry {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    '_c2rust_label: {
        if !list_append(&raw mut list, &raw mut variable1 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable1) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                39 as ::core::ffi::c_uint,
                b"ListEntry *generate_list(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if !list_append(&raw mut list, &raw mut variable2 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable2) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                40 as ::core::ffi::c_uint,
                b"ListEntry *generate_list(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if !list_append(&raw mut list, &raw mut variable3 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable3) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                41 as ::core::ffi::c_uint,
                b"ListEntry *generate_list(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if !list_append(&raw mut list, &raw mut variable4 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable4) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                42 as ::core::ffi::c_uint,
                b"ListEntry *generate_list(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    return list;
}
#[no_mangle]
pub unsafe extern "C" fn check_list_integrity(mut list: *mut ListEntry) {
    let mut prev: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut rover: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    prev = ::core::ptr::null_mut::<ListEntry>();
    rover = list;
    while !rover.is_null() {
        '_c2rust_label: {
            if list_prev(rover) == prev {
            } else {
                __assert_fail(
                    b"list_prev(rover) == prev\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    56 as ::core::ffi::c_uint,
                    b"void check_list_integrity(ListEntry *)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        prev = rover;
        rover = list_next(rover);
    }
}
#[no_mangle]
pub unsafe extern "C" fn test_list_append() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    '_c2rust_label: {
        if !list_append(&raw mut list, &raw mut variable1 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable1) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                66 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_0: {
        if !list_append(&raw mut list, &raw mut variable2 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable2) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                68 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_1: {
        if !list_append(&raw mut list, &raw mut variable3 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable3) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                70 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_2: {
        if !list_append(&raw mut list, &raw mut variable4 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable4) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                72 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_3: {
        if list_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                75 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if list_nth_data(list, 0 as ::core::ffi::c_uint) == &raw mut variable1 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 0) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                77 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if list_nth_data(list, 1 as ::core::ffi::c_uint) == &raw mut variable2 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 1) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                78 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if list_nth_data(list, 2 as ::core::ffi::c_uint) == &raw mut variable3 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 2) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                79 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if list_nth_data(list, 3 as ::core::ffi::c_uint) == &raw mut variable4 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 3) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                80 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_8: {
        if list_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                85 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_9: {
        if list_append(&raw mut list, &raw mut variable1 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable1) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                86 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_10: {
        if list_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                87 as ::core::ffi::c_uint,
                b"void test_list_append(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_prepend() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    '_c2rust_label: {
        if !list_prepend(&raw mut list, &raw mut variable1 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_prepend(&list, &variable1) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                97 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_0: {
        if !list_prepend(&raw mut list, &raw mut variable2 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_prepend(&list, &variable2) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                99 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_1: {
        if !list_prepend(&raw mut list, &raw mut variable3 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_prepend(&list, &variable3) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                101 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_2: {
        if !list_prepend(&raw mut list, &raw mut variable4 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_prepend(&list, &variable4) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                103 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_3: {
        if list_nth_data(list, 0 as ::core::ffi::c_uint) == &raw mut variable4 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 0) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                106 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if list_nth_data(list, 1 as ::core::ffi::c_uint) == &raw mut variable3 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 1) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                107 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if list_nth_data(list, 2 as ::core::ffi::c_uint) == &raw mut variable2 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 2) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                108 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if list_nth_data(list, 3 as ::core::ffi::c_uint) == &raw mut variable1 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 3) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                109 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_7: {
        if list_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                114 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if list_prepend(&raw mut list, &raw mut variable1 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_prepend(&list, &variable1) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                115 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_9: {
        if list_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                116 as ::core::ffi::c_uint,
                b"void test_list_prepend(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_free() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    list = generate_list();
    list_free(list);
    list_free(::core::ptr::null_mut::<ListEntry>());
}
#[no_mangle]
pub unsafe extern "C" fn test_list_next() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut rover: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    list = generate_list();
    rover = list;
    '_c2rust_label: {
        if list_data(rover) == &raw mut variable1 as ListValue {
        } else {
            __assert_fail(
                b"list_data(rover) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                145 as ::core::ffi::c_uint,
                b"void test_list_next(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    rover = list_next(rover);
    '_c2rust_label_0: {
        if list_data(rover) == &raw mut variable2 as ListValue {
        } else {
            __assert_fail(
                b"list_data(rover) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                147 as ::core::ffi::c_uint,
                b"void test_list_next(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    rover = list_next(rover);
    '_c2rust_label_1: {
        if list_data(rover) == &raw mut variable3 as ListValue {
        } else {
            __assert_fail(
                b"list_data(rover) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                149 as ::core::ffi::c_uint,
                b"void test_list_next(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    rover = list_next(rover);
    '_c2rust_label_2: {
        if list_data(rover) == &raw mut variable4 as ListValue {
        } else {
            __assert_fail(
                b"list_data(rover) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                151 as ::core::ffi::c_uint,
                b"void test_list_next(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    rover = list_next(rover);
    '_c2rust_label_3: {
        if rover.is_null() {
        } else {
            __assert_fail(
                b"rover == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                153 as ::core::ffi::c_uint,
                b"void test_list_next(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_nth_entry() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut entry: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    list = generate_list();
    entry = list_nth_entry(list, 0 as ::core::ffi::c_uint);
    '_c2rust_label: {
        if list_data(entry) == &raw mut variable1 as ListValue {
        } else {
            __assert_fail(
                b"list_data(entry) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                168 as ::core::ffi::c_uint,
                b"void test_list_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = list_nth_entry(list, 1 as ::core::ffi::c_uint);
    '_c2rust_label_0: {
        if list_data(entry) == &raw mut variable2 as ListValue {
        } else {
            __assert_fail(
                b"list_data(entry) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                170 as ::core::ffi::c_uint,
                b"void test_list_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = list_nth_entry(list, 2 as ::core::ffi::c_uint);
    '_c2rust_label_1: {
        if list_data(entry) == &raw mut variable3 as ListValue {
        } else {
            __assert_fail(
                b"list_data(entry) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                172 as ::core::ffi::c_uint,
                b"void test_list_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = list_nth_entry(list, 3 as ::core::ffi::c_uint);
    '_c2rust_label_2: {
        if list_data(entry) == &raw mut variable4 as ListValue {
        } else {
            __assert_fail(
                b"list_data(entry) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                174 as ::core::ffi::c_uint,
                b"void test_list_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = list_nth_entry(list, 4 as ::core::ffi::c_uint);
    '_c2rust_label_3: {
        if entry.is_null() {
        } else {
            __assert_fail(
                b"entry == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                179 as ::core::ffi::c_uint,
                b"void test_list_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    entry = list_nth_entry(list, 400 as ::core::ffi::c_uint);
    '_c2rust_label_4: {
        if entry.is_null() {
        } else {
            __assert_fail(
                b"entry == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                181 as ::core::ffi::c_uint,
                b"void test_list_nth_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_nth_data() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    list = generate_list();
    '_c2rust_label: {
        if list_nth_data(list, 0 as ::core::ffi::c_uint) == &raw mut variable1 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 0) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                194 as ::core::ffi::c_uint,
                b"void test_list_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if list_nth_data(list, 1 as ::core::ffi::c_uint) == &raw mut variable2 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 1) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                195 as ::core::ffi::c_uint,
                b"void test_list_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if list_nth_data(list, 2 as ::core::ffi::c_uint) == &raw mut variable3 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 2) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                196 as ::core::ffi::c_uint,
                b"void test_list_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if list_nth_data(list, 3 as ::core::ffi::c_uint) == &raw mut variable4 as ListValue {
        } else {
            __assert_fail(
                b"list_nth_data(list, 3) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                197 as ::core::ffi::c_uint,
                b"void test_list_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if list_nth_data(list, 4 as ::core::ffi::c_uint).is_null() {
        } else {
            __assert_fail(
                b"list_nth_data(list, 4) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                201 as ::core::ffi::c_uint,
                b"void test_list_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if list_nth_data(list, 400 as ::core::ffi::c_uint).is_null() {
        } else {
            __assert_fail(
                b"list_nth_data(list, 400) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                202 as ::core::ffi::c_uint,
                b"void test_list_nth_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_length() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    list = generate_list();
    '_c2rust_label: {
        if list_length(list) == 4 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 4\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                215 as ::core::ffi::c_uint,
                b"void test_list_length(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if !list_prepend(&raw mut list, &raw mut variable1 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_prepend(&list, &variable1) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                219 as ::core::ffi::c_uint,
                b"void test_list_length(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if list_length(list) == 5 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 5\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                221 as ::core::ffi::c_uint,
                b"void test_list_length(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list_free(list);
    '_c2rust_label_2: {
        if list_length(::core::ptr::null_mut::<ListEntry>()) == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(NULL) == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                227 as ::core::ffi::c_uint,
                b"void test_list_length(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_list_remove_entry() {
    let mut empty_list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut entry: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    list = generate_list();
    entry = list_nth_entry(list, 2 as ::core::ffi::c_uint);
    '_c2rust_label: {
        if list_remove_entry(&raw mut list, entry) != 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"list_remove_entry(&list, entry) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                241 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if list_length(list) == 3 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 3\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                242 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    entry = list_nth_entry(list, 0 as ::core::ffi::c_uint);
    '_c2rust_label_1: {
        if list_remove_entry(&raw mut list, entry) != 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"list_remove_entry(&list, entry) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                248 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if list_length(list) == 2 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 2\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                249 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    '_c2rust_label_3: {
        if list_remove_entry(&raw mut list, ::core::ptr::null_mut::<ListEntry>())
            == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"list_remove_entry(&list, NULL) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                256 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if list_remove_entry(&raw mut empty_list, ::core::ptr::null_mut::<ListEntry>())
            == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"list_remove_entry(&empty_list, NULL) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                260 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list_free(list);
    list = ::core::ptr::null_mut::<ListEntry>();
    '_c2rust_label_5: {
        if !list_append(&raw mut list, &raw mut variable1 as ListValue).is_null() {
        } else {
            __assert_fail(
                b"list_append(&list, &variable1) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                267 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if !list.is_null() {
        } else {
            __assert_fail(
                b"list != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                268 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if list_remove_entry(&raw mut list, list) != 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"list_remove_entry(&list, list) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                269 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if list.is_null() {
        } else {
            __assert_fail(
                b"list == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                270 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list = generate_list();
    entry = list_nth_entry(list, 3 as ::core::ffi::c_uint);
    '_c2rust_label_9: {
        if list_remove_entry(&raw mut list, entry) != 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"list_remove_entry(&list, entry) != 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                276 as ::core::ffi::c_uint,
                b"void test_list_remove_entry(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_remove_data() {
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
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut i: ::core::ffi::c_uint = 0;
    list = ::core::ptr::null_mut::<ListEntry>();
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        '_c2rust_label: {
            if !list_prepend(
                &raw mut list,
                (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as ListValue,
            )
            .is_null()
            {
            } else {
                __assert_fail(
                    b"list_prepend(&list, &entries[i]) != NULL\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    294 as ::core::ffi::c_uint,
                    b"void test_list_remove_data(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    val = 0 as ::core::ffi::c_int;
    '_c2rust_label_0: {
        if list_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ListValue,
        ) == 0 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"list_remove_data(&list, int_equal, &val) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                300 as ::core::ffi::c_uint,
                b"void test_list_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    val = 56 as ::core::ffi::c_int;
    '_c2rust_label_1: {
        if list_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ListValue,
        ) == 0 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"list_remove_data(&list, int_equal, &val) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                302 as ::core::ffi::c_uint,
                b"void test_list_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    val = 8 as ::core::ffi::c_int;
    '_c2rust_label_2: {
        if list_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ListValue,
        ) == 1 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"list_remove_data(&list, int_equal, &val) == 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                308 as ::core::ffi::c_uint,
                b"void test_list_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if list_length(list) == num_entries.wrapping_sub(1 as ::core::ffi::c_uint) {
        } else {
            __assert_fail(
                b"list_length(list) == num_entries - 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                309 as ::core::ffi::c_uint,
                b"void test_list_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    val = 4 as ::core::ffi::c_int;
    '_c2rust_label_4: {
        if list_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ListValue,
        ) == 4 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"list_remove_data(&list, int_equal, &val) == 4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                315 as ::core::ffi::c_uint,
                b"void test_list_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if list_length(list) == num_entries.wrapping_sub(5 as ::core::ffi::c_uint) {
        } else {
            __assert_fail(
                b"list_length(list) == num_entries - 5\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                316 as ::core::ffi::c_uint,
                b"void test_list_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    val = 89 as ::core::ffi::c_int;
    '_c2rust_label_6: {
        if list_remove_data(
            &raw mut list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ListValue,
        ) == 1 as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"list_remove_data(&list, int_equal, &val) == 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                322 as ::core::ffi::c_uint,
                b"void test_list_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if list_length(list) == num_entries.wrapping_sub(6 as ::core::ffi::c_uint) {
        } else {
            __assert_fail(
                b"list_length(list) == num_entries - 6\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                323 as ::core::ffi::c_uint,
                b"void test_list_remove_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_list_integrity(list);
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_sort() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
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
    list = ::core::ptr::null_mut::<ListEntry>();
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        '_c2rust_label: {
            if !list_prepend(
                &raw mut list,
                (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as ListValue,
            )
            .is_null()
            {
            } else {
                __assert_fail(
                    b"list_prepend(&list, &entries[i]) != NULL\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    340 as ::core::ffi::c_uint,
                    b"void test_list_sort(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    list_sort(
        &raw mut list,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_0: {
        if list_length(list) == num_entries {
        } else {
            __assert_fail(
                b"list_length(list) == num_entries\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                347 as ::core::ffi::c_uint,
                b"void test_list_sort(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
        value = list_nth_data(list, i) as *mut ::core::ffi::c_int;
        '_c2rust_label_1: {
            if *value == sorted[i as usize] {
            } else {
                __assert_fail(
                    b"*value == sorted[i]\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    355 as ::core::ffi::c_uint,
                    b"void test_list_sort(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    list_free(list);
    list = ::core::ptr::null_mut::<ListEntry>();
    list_sort(
        &raw mut list,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_2: {
        if list.is_null() {
        } else {
            __assert_fail(
                b"list == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                366 as ::core::ffi::c_uint,
                b"void test_list_sort(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_list_find_data() {
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
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut result: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut i: ::core::ffi::c_int = 0;
    let mut val: ::core::ffi::c_int = 0;
    let mut data: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    list = ::core::ptr::null_mut::<ListEntry>();
    i = 0 as ::core::ffi::c_int;
    while i < num_entries {
        '_c2rust_label: {
            if !list_append(
                &raw mut list,
                (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as ListValue,
            )
            .is_null()
            {
            } else {
                __assert_fail(
                    b"list_append(&list, &entries[i]) != NULL\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    383 as ::core::ffi::c_uint,
                    b"void test_list_find_data(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    i = 0 as ::core::ffi::c_int;
    while i < num_entries {
        val = entries[i as usize];
        result = list_find_data(
            list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ListValue,
        );
        '_c2rust_label_0: {
            if !result.is_null() {
            } else {
                __assert_fail(
                    b"result != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    394 as ::core::ffi::c_uint,
                    b"void test_list_find_data(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        data = list_data(result) as *mut ::core::ffi::c_int;
        '_c2rust_label_1: {
            if *data == val {
            } else {
                __assert_fail(
                    b"*data == val\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    397 as ::core::ffi::c_uint,
                    b"void test_list_find_data(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    val = 0 as ::core::ffi::c_int;
    '_c2rust_label_2: {
        if list_find_data(
            list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ListValue,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"list_find_data(list, int_equal, &val) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                403 as ::core::ffi::c_uint,
                b"void test_list_find_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    val = 56 as ::core::ffi::c_int;
    '_c2rust_label_3: {
        if list_find_data(
            list,
            Some(
                int_equal
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
            &raw mut val as ListValue,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"list_find_data(list, int_equal, &val) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                405 as ::core::ffi::c_uint,
                b"void test_list_find_data(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_to_array() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut array: *mut *mut ::core::ffi::c_void =
        ::core::ptr::null_mut::<*mut ::core::ffi::c_void>();
    list = generate_list();
    array = list_to_array(list) as *mut *mut ::core::ffi::c_void;
    '_c2rust_label: {
        if *array.offset(0 as ::core::ffi::c_int as isize)
            == &raw mut variable1 as *mut ::core::ffi::c_void
        {
        } else {
            __assert_fail(
                b"array[0] == &variable1\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                419 as ::core::ffi::c_uint,
                b"void test_list_to_array(void)\0" as *const u8
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
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                420 as ::core::ffi::c_uint,
                b"void test_list_to_array(void)\0" as *const u8
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
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                421 as ::core::ffi::c_uint,
                b"void test_list_to_array(void)\0" as *const u8
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
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                422 as ::core::ffi::c_uint,
                b"void test_list_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_free(array as *mut ::core::ffi::c_void);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    array = list_to_array(list) as *mut *mut ::core::ffi::c_void;
    '_c2rust_label_3: {
        if array.is_null() {
        } else {
            __assert_fail(
                b"array == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                431 as ::core::ffi::c_uint,
                b"void test_list_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list_free(list);
}
#[no_mangle]
pub unsafe extern "C" fn test_list_iterate() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut iter: ListIterator = _ListIterator {
        prev_next: ::core::ptr::null_mut::<*mut ListEntry>(),
        current: ::core::ptr::null_mut::<ListEntry>(),
    };
    let mut i: ::core::ffi::c_int = 0;
    let mut a: ::core::ffi::c_int = 0;
    let mut counter: ::core::ffi::c_int = 0;
    let mut data: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    list = ::core::ptr::null_mut::<ListEntry>();
    i = 0 as ::core::ffi::c_int;
    while i < 50 as ::core::ffi::c_int {
        '_c2rust_label: {
            if !list_prepend(&raw mut list, &raw mut a as ListValue).is_null() {
            } else {
                __assert_fail(
                    b"list_prepend(&list, &a) != NULL\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    450 as ::core::ffi::c_uint,
                    b"void test_list_iterate(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    counter = 0 as ::core::ffi::c_int;
    list_iterate(&raw mut list, &raw mut iter);
    list_iter_remove(&raw mut iter);
    while list_iter_has_more(&raw mut iter) != 0 {
        data = list_iter_next(&raw mut iter) as *mut ::core::ffi::c_int;
        counter += 1;
        if counter % 2 as ::core::ffi::c_int == 0 as ::core::ffi::c_int {
            list_iter_remove(&raw mut iter);
            list_iter_remove(&raw mut iter);
        }
    }
    '_c2rust_label_0: {
        if list_iter_next(&raw mut iter).is_null() {
        } else {
            __assert_fail(
                b"list_iter_next(&iter) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                482 as ::core::ffi::c_uint,
                b"void test_list_iterate(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list_iter_remove(&raw mut iter);
    '_c2rust_label_1: {
        if counter == 50 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"counter == 50\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                488 as ::core::ffi::c_uint,
                b"void test_list_iterate(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if list_length(list) == 25 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"list_length(list) == 25\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                489 as ::core::ffi::c_uint,
                b"void test_list_iterate(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    list_free(list);
    list = ::core::ptr::null_mut::<ListEntry>();
    counter = 0 as ::core::ffi::c_int;
    list_iterate(&raw mut list, &raw mut iter);
    while list_iter_has_more(&raw mut iter) != 0 {
        data = list_iter_next(&raw mut iter) as *mut ::core::ffi::c_int;
        counter += 1;
    }
    '_c2rust_label_3: {
        if counter == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"counter == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                505 as ::core::ffi::c_uint,
                b"void test_list_iterate(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_list_iterate_bad_remove() {
    let mut list: *mut ListEntry = ::core::ptr::null_mut::<ListEntry>();
    let mut iter: ListIterator = _ListIterator {
        prev_next: ::core::ptr::null_mut::<*mut ListEntry>(),
        current: ::core::ptr::null_mut::<ListEntry>(),
    };
    let mut values: [::core::ffi::c_int; 49] = [0; 49];
    let mut i: ::core::ffi::c_int = 0;
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    list = ::core::ptr::null_mut::<ListEntry>();
    i = 0 as ::core::ffi::c_int;
    while i < 49 as ::core::ffi::c_int {
        values[i as usize] = i;
        '_c2rust_label: {
            if !list_prepend(
                &raw mut list,
                (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as ListValue,
            )
            .is_null()
            {
            } else {
                __assert_fail(
                    b"list_prepend(&list, &values[i]) != NULL\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    525 as ::core::ffi::c_uint,
                    b"void test_list_iterate_bad_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    list_iterate(&raw mut list, &raw mut iter);
    while list_iter_has_more(&raw mut iter) != 0 {
        val = list_iter_next(&raw mut iter) as *mut ::core::ffi::c_int;
        if *val % 2 as ::core::ffi::c_int == 0 as ::core::ffi::c_int {
            '_c2rust_label_0: {
                if list_remove_data(
                    &raw mut list,
                    Some(
                        int_equal
                            as unsafe extern "C" fn(
                                *mut ::core::ffi::c_void,
                                *mut ::core::ffi::c_void,
                            )
                                -> ::core::ffi::c_int,
                    ),
                    val as ListValue,
                ) != 0 as ::core::ffi::c_uint
                {
                } else {
                    __assert_fail(
                        b"list_remove_data(&list, int_equal, val) != 0\0" as *const u8
                            as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-list.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        542 as ::core::ffi::c_uint,
                        b"void test_list_iterate_bad_remove(void)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
            list_iter_remove(&raw mut iter);
        }
    }
    list_free(list);
}
static mut tests: [UnitTestFunction; 15] = unsafe {
    [
        Some(test_list_append as unsafe extern "C" fn() -> ()),
        Some(test_list_prepend as unsafe extern "C" fn() -> ()),
        Some(test_list_free as unsafe extern "C" fn() -> ()),
        Some(test_list_next as unsafe extern "C" fn() -> ()),
        Some(test_list_nth_entry as unsafe extern "C" fn() -> ()),
        Some(test_list_nth_data as unsafe extern "C" fn() -> ()),
        Some(test_list_length as unsafe extern "C" fn() -> ()),
        Some(test_list_remove_entry as unsafe extern "C" fn() -> ()),
        Some(test_list_remove_data as unsafe extern "C" fn() -> ()),
        Some(test_list_sort as unsafe extern "C" fn() -> ()),
        Some(test_list_find_data as unsafe extern "C" fn() -> ()),
        Some(test_list_to_array as unsafe extern "C" fn() -> ()),
        Some(test_list_iterate as unsafe extern "C" fn() -> ()),
        Some(test_list_iterate_bad_remove as unsafe extern "C" fn() -> ()),
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
