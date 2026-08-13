extern "C" {
    pub type _Set;
    pub type _SetEntry;
    fn sprintf(
        __s: *mut ::core::ffi::c_char,
        __format: *const ::core::ffi::c_char,
        ...
    ) -> ::core::ffi::c_int;
    fn atoi(__nptr: *const ::core::ffi::c_char) -> ::core::ffi::c_int;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_strdup(string: *const ::core::ffi::c_char) -> *mut ::core::ffi::c_char;
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn alloc_test_get_allocated() -> size_t;
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn set_new(hash_func: SetHashFunc, equal_func: SetEqualFunc) -> *mut Set;
    fn set_free(set: *mut Set);
    fn set_register_free_function(set: *mut Set, free_func: SetFreeFunc);
    fn set_insert(set: *mut Set, data: SetValue) -> ::core::ffi::c_int;
    fn set_remove(set: *mut Set, data: SetValue) -> ::core::ffi::c_int;
    fn set_query(set: *mut Set, data: SetValue) -> ::core::ffi::c_int;
    fn set_num_entries(set: *mut Set) -> ::core::ffi::c_uint;
    fn set_to_array(set: *mut Set) -> *mut SetValue;
    fn set_union(set1: *mut Set, set2: *mut Set) -> *mut Set;
    fn set_intersection(set1: *mut Set, set2: *mut Set) -> *mut Set;
    fn set_iterate(set: *mut Set, iter: *mut SetIterator);
    fn set_iter_has_more(iterator: *mut SetIterator) -> ::core::ffi::c_int;
    fn set_iter_next(iterator: *mut SetIterator) -> SetValue;
    fn int_equal(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn int_hash(location: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
    fn pointer_equal(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn pointer_hash(location: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
    fn string_equal(
        string1: *mut ::core::ffi::c_void,
        string2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn string_hash(string: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type Set = _Set;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _SetIterator {
    pub set: *mut Set,
    pub next_entry: *mut SetEntry,
    pub next_chain: ::core::ffi::c_uint,
}
pub type SetEntry = _SetEntry;
pub type SetIterator = _SetIterator;
pub type SetValue = *mut ::core::ffi::c_void;
pub type SetHashFunc = Option<unsafe extern "C" fn(SetValue) -> ::core::ffi::c_uint>;
pub type SetEqualFunc = Option<unsafe extern "C" fn(SetValue, SetValue) -> ::core::ffi::c_int>;
pub type SetFreeFunc = Option<unsafe extern "C" fn(SetValue) -> ()>;
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
#[no_mangle]
pub static mut allocated_values: ::core::ffi::c_int = 0;
#[no_mangle]
pub unsafe extern "C" fn generate_set() -> *mut Set {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    let mut i: ::core::ffi::c_uint = 0;
    let mut value: *mut ::core::ffi::c_char = ::core::ptr::null_mut::<::core::ffi::c_char>();
    set = set_new(
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            string_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_uint;
    while i < 10000 as ::core::ffi::c_uint {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        value = alloc_test_strdup(&raw mut buf as *mut ::core::ffi::c_char);
        set_insert(set, value as SetValue);
        '_c2rust_label: {
            if set_num_entries(set) == i.wrapping_add(1 as ::core::ffi::c_uint) {
            } else {
                __assert_fail(
                    b"set_num_entries(set) == i + 1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    57 as ::core::ffi::c_uint,
                    b"Set *generate_set(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    set_register_free_function(
        set,
        Some(alloc_test_free as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ()),
    );
    return set;
}
#[no_mangle]
pub unsafe extern "C" fn test_set_new_free() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut i: ::core::ffi::c_int = 0;
    let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    set = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    set_register_free_function(
        set,
        Some(alloc_test_free as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ()),
    );
    '_c2rust_label: {
        if !set.is_null() {
        } else {
            __assert_fail(
                b"set != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                75 as ::core::ffi::c_uint,
                b"void test_set_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < 10000 as ::core::ffi::c_int {
        value = alloc_test_malloc(::core::mem::size_of::<::core::ffi::c_int>() as size_t)
            as *mut ::core::ffi::c_int;
        *value = i;
        set_insert(set, value as SetValue);
        i += 1;
    }
    set_free(set);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    set = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_0: {
        if set.is_null() {
        } else {
            __assert_fail(
                b"set == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                95 as ::core::ffi::c_uint,
                b"void test_set_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(1 as ::core::ffi::c_int);
    set = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_1: {
        if set.is_null() {
        } else {
            __assert_fail(
                b"set == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                99 as ::core::ffi::c_uint,
                b"void test_set_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if alloc_test_get_allocated() == 0 as size_t {
        } else {
            __assert_fail(
                b"alloc_test_get_allocated() == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                100 as ::core::ffi::c_uint,
                b"void test_set_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_set_insert() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut numbers1: [::core::ffi::c_int; 6] = [
        1 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        3 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        5 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
    ];
    let mut numbers2: [::core::ffi::c_int; 6] = [
        5 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        9 as ::core::ffi::c_int,
        10 as ::core::ffi::c_int,
    ];
    let mut i: ::core::ffi::c_int = 0;
    set = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < 6 as ::core::ffi::c_int {
        set_insert(
            set,
            (&raw mut numbers1 as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SetValue,
        );
        i += 1;
    }
    i = 0 as ::core::ffi::c_int;
    while i < 6 as ::core::ffi::c_int {
        set_insert(
            set,
            (&raw mut numbers2 as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SetValue,
        );
        i += 1;
    }
    '_c2rust_label: {
        if set_num_entries(set) == 10 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"set_num_entries(set) == 10\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                122 as ::core::ffi::c_uint,
                b"void test_set_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set);
}
#[no_mangle]
pub unsafe extern "C" fn test_set_query() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    let mut i: ::core::ffi::c_int = 0;
    set = generate_set();
    i = 0 as ::core::ffi::c_int;
    while i < 10000 as ::core::ffi::c_int {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        '_c2rust_label: {
            if set_query(set, &raw mut buf as *mut ::core::ffi::c_char as SetValue)
                != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_query(set, buf) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    139 as ::core::ffi::c_uint,
                    b"void test_set_query(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    '_c2rust_label_0: {
        if set_query(
            set,
            b"-1\0" as *const u8 as *const ::core::ffi::c_char as SetValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"set_query(set, \"-1\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                144 as ::core::ffi::c_uint,
                b"void test_set_query(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if set_query(
            set,
            b"100001\0" as *const u8 as *const ::core::ffi::c_char as SetValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"set_query(set, \"100001\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                145 as ::core::ffi::c_uint,
                b"void test_set_query(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set);
}
#[no_mangle]
pub unsafe extern "C" fn test_set_remove() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    let mut i: ::core::ffi::c_int = 0;
    let mut num_entries: ::core::ffi::c_uint = 0;
    set = generate_set();
    num_entries = set_num_entries(set);
    '_c2rust_label: {
        if num_entries == 10000 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"num_entries == 10000\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                160 as ::core::ffi::c_uint,
                b"void test_set_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 4000 as ::core::ffi::c_int;
    while i < 6000 as ::core::ffi::c_int {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        '_c2rust_label_0: {
            if set_query(set, &raw mut buf as *mut ::core::ffi::c_char as SetValue)
                != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_query(set, buf) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    170 as ::core::ffi::c_uint,
                    b"void test_set_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_1: {
            if set_remove(set, &raw mut buf as *mut ::core::ffi::c_char as SetValue)
                != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_remove(set, buf) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    174 as ::core::ffi::c_uint,
                    b"void test_set_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_2: {
            if set_num_entries(set) == num_entries.wrapping_sub(1 as ::core::ffi::c_uint) {
            } else {
                __assert_fail(
                    b"set_num_entries(set) == num_entries - 1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    178 as ::core::ffi::c_uint,
                    b"void test_set_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_3: {
            if set_query(set, &raw mut buf as *mut ::core::ffi::c_char as SetValue)
                == 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_query(set, buf) == 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    182 as ::core::ffi::c_uint,
                    b"void test_set_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        num_entries = num_entries.wrapping_sub(1);
        i += 1;
    }
    i = -(1000 as ::core::ffi::c_int);
    while i < -(500 as ::core::ffi::c_int) {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        '_c2rust_label_4: {
            if set_remove(set, &raw mut buf as *mut ::core::ffi::c_char as SetValue)
                == 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_remove(set, buf) == 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    192 as ::core::ffi::c_uint,
                    b"void test_set_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_5: {
            if set_num_entries(set) == num_entries {
            } else {
                __assert_fail(
                    b"set_num_entries(set) == num_entries\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    193 as ::core::ffi::c_uint,
                    b"void test_set_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    i = 50000 as ::core::ffi::c_int;
    while i < 51000 as ::core::ffi::c_int {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        '_c2rust_label_6: {
            if set_remove(set, &raw mut buf as *mut ::core::ffi::c_char as SetValue)
                == 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_remove(set, buf) == 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    199 as ::core::ffi::c_uint,
                    b"void test_set_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_7: {
            if set_num_entries(set) == num_entries {
            } else {
                __assert_fail(
                    b"set_num_entries(set) == num_entries\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    200 as ::core::ffi::c_uint,
                    b"void test_set_remove(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    set_free(set);
}
#[no_mangle]
pub unsafe extern "C" fn test_set_union() {
    let mut numbers1: [::core::ffi::c_int; 7] = [
        1 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        3 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        5 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
    ];
    let mut numbers2: [::core::ffi::c_int; 7] = [
        5 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        9 as ::core::ffi::c_int,
        10 as ::core::ffi::c_int,
        11 as ::core::ffi::c_int,
    ];
    let mut result: [::core::ffi::c_int; 11] = [
        1 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        3 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        5 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        9 as ::core::ffi::c_int,
        10 as ::core::ffi::c_int,
        11 as ::core::ffi::c_int,
    ];
    let mut i: ::core::ffi::c_int = 0;
    let mut set1: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut set2: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut result_set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut allocated: size_t = 0;
    set1 = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < 7 as ::core::ffi::c_int {
        set_insert(
            set1,
            (&raw mut numbers1 as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SetValue,
        );
        i += 1;
    }
    set2 = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < 7 as ::core::ffi::c_int {
        set_insert(
            set2,
            (&raw mut numbers2 as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SetValue,
        );
        i += 1;
    }
    result_set = set_union(set1, set2);
    '_c2rust_label: {
        if set_num_entries(result_set) == 11 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"set_num_entries(result_set) == 11\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                237 as ::core::ffi::c_uint,
                b"void test_set_union(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < 11 as ::core::ffi::c_int {
        '_c2rust_label_0: {
            if set_query(
                result_set,
                (&raw mut result as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as SetValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_query(result_set, &result[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    240 as ::core::ffi::c_uint,
                    b"void test_set_union(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    set_free(result_set);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_1: {
        if set_union(set1, set2).is_null() {
        } else {
            __assert_fail(
                b"set_union(set1, set2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                248 as ::core::ffi::c_uint,
                b"void test_set_union(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(2 as ::core::ffi::c_int + 2 as ::core::ffi::c_int);
    allocated = alloc_test_get_allocated();
    '_c2rust_label_2: {
        if set_union(set1, set2).is_null() {
        } else {
            __assert_fail(
                b"set_union(set1, set2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                254 as ::core::ffi::c_uint,
                b"void test_set_union(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if alloc_test_get_allocated() == allocated {
        } else {
            __assert_fail(
                b"alloc_test_get_allocated() == allocated\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                255 as ::core::ffi::c_uint,
                b"void test_set_union(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(
        2 as ::core::ffi::c_int + 7 as ::core::ffi::c_int + 2 as ::core::ffi::c_int,
    );
    allocated = alloc_test_get_allocated();
    '_c2rust_label_4: {
        if set_union(set1, set2).is_null() {
        } else {
            __assert_fail(
                b"set_union(set1, set2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                262 as ::core::ffi::c_uint,
                b"void test_set_union(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if alloc_test_get_allocated() == allocated {
        } else {
            __assert_fail(
                b"alloc_test_get_allocated() == allocated\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                263 as ::core::ffi::c_uint,
                b"void test_set_union(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set1);
    set_free(set2);
}
#[no_mangle]
pub unsafe extern "C" fn test_set_intersection() {
    let mut numbers1: [::core::ffi::c_int; 7] = [
        1 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        3 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        5 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
    ];
    let mut numbers2: [::core::ffi::c_int; 7] = [
        5 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        9 as ::core::ffi::c_int,
        10 as ::core::ffi::c_int,
        11 as ::core::ffi::c_int,
    ];
    let mut result: [::core::ffi::c_int; 3] = [
        5 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
    ];
    let mut i: ::core::ffi::c_int = 0;
    let mut set1: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut set2: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut result_set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut allocated: size_t = 0;
    set1 = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < 7 as ::core::ffi::c_int {
        set_insert(
            set1,
            (&raw mut numbers1 as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SetValue,
        );
        i += 1;
    }
    set2 = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < 7 as ::core::ffi::c_int {
        set_insert(
            set2,
            (&raw mut numbers2 as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SetValue,
        );
        i += 1;
    }
    result_set = set_intersection(set1, set2);
    '_c2rust_label: {
        if set_num_entries(result_set) == 3 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"set_num_entries(result_set) == 3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                300 as ::core::ffi::c_uint,
                b"void test_set_intersection(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < 3 as ::core::ffi::c_int {
        '_c2rust_label_0: {
            if set_query(
                result_set,
                (&raw mut result as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as SetValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_query(result_set, &result[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    303 as ::core::ffi::c_uint,
                    b"void test_set_intersection(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_1: {
        if set_intersection(set1, set2).is_null() {
        } else {
            __assert_fail(
                b"set_intersection(set1, set2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                309 as ::core::ffi::c_uint,
                b"void test_set_intersection(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(2 as ::core::ffi::c_int + 2 as ::core::ffi::c_int);
    allocated = alloc_test_get_allocated();
    '_c2rust_label_2: {
        if set_intersection(set1, set2).is_null() {
        } else {
            __assert_fail(
                b"set_intersection(set1, set2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                315 as ::core::ffi::c_uint,
                b"void test_set_intersection(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if alloc_test_get_allocated() == allocated {
        } else {
            __assert_fail(
                b"alloc_test_get_allocated() == allocated\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                316 as ::core::ffi::c_uint,
                b"void test_set_intersection(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set1);
    set_free(set2);
    set_free(result_set);
}
#[no_mangle]
pub unsafe extern "C" fn test_set_to_array() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut values: [::core::ffi::c_int; 100] = [0; 100];
    let mut array: *mut *mut ::core::ffi::c_int =
        ::core::ptr::null_mut::<*mut ::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    set = set_new(
        Some(pointer_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            pointer_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < 100 as ::core::ffi::c_int {
        values[i as usize] = 1 as ::core::ffi::c_int;
        set_insert(
            set,
            (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as SetValue,
        );
        i += 1;
    }
    array = set_to_array(set) as *mut *mut ::core::ffi::c_int;
    i = 0 as ::core::ffi::c_int;
    while i < 100 as ::core::ffi::c_int {
        '_c2rust_label: {
            if **array.offset(i as isize) == 1 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"*array[i] == 1\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    345 as ::core::ffi::c_uint,
                    b"void test_set_to_array(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        **array.offset(i as isize) = 0 as ::core::ffi::c_int;
        i += 1;
    }
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_0: {
        if set_to_array(set).is_null() {
        } else {
            __assert_fail(
                b"set_to_array(set) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                352 as ::core::ffi::c_uint,
                b"void test_set_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_free(array as *mut ::core::ffi::c_void);
    set_free(set);
}
#[no_mangle]
pub unsafe extern "C" fn test_set_iterating() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut iterator: SetIterator = _SetIterator {
        set: ::core::ptr::null_mut::<Set>(),
        next_entry: ::core::ptr::null_mut::<SetEntry>(),
        next_chain: 0,
    };
    let mut count: ::core::ffi::c_int = 0;
    set = generate_set();
    count = 0 as ::core::ffi::c_int;
    set_iterate(set, &raw mut iterator);
    while set_iter_has_more(&raw mut iterator) != 0 {
        set_iter_next(&raw mut iterator);
        count += 1;
    }
    '_c2rust_label: {
        if set_iter_next(&raw mut iterator).is_null() {
        } else {
            __assert_fail(
                b"set_iter_next(&iterator) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                380 as ::core::ffi::c_uint,
                b"void test_set_iterating(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if count == 10000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"count == 10000\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                384 as ::core::ffi::c_uint,
                b"void test_set_iterating(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set);
    set = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    set_iterate(set, &raw mut iterator);
    '_c2rust_label_1: {
        if set_iter_has_more(&raw mut iterator) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"set_iter_has_more(&iterator) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                394 as ::core::ffi::c_uint,
                b"void test_set_iterating(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set);
}
#[no_mangle]
pub unsafe extern "C" fn test_set_iterating_remove() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut iterator: SetIterator = _SetIterator {
        set: ::core::ptr::null_mut::<Set>(),
        next_entry: ::core::ptr::null_mut::<SetEntry>(),
        next_chain: 0,
    };
    let mut count: ::core::ffi::c_int = 0;
    let mut removed: ::core::ffi::c_uint = 0;
    let mut value: *mut ::core::ffi::c_char = ::core::ptr::null_mut::<::core::ffi::c_char>();
    set = generate_set();
    count = 0 as ::core::ffi::c_int;
    removed = 0 as ::core::ffi::c_uint;
    set_iterate(set, &raw mut iterator);
    while set_iter_has_more(&raw mut iterator) != 0 {
        value = set_iter_next(&raw mut iterator) as *mut ::core::ffi::c_char;
        if atoi(value) % 100 as ::core::ffi::c_int == 0 as ::core::ffi::c_int {
            set_remove(set, value as SetValue);
            removed = removed.wrapping_add(1);
        }
        count += 1;
    }
    '_c2rust_label: {
        if count == 10000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"count == 10000\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                438 as ::core::ffi::c_uint,
                b"void test_set_iterating_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if removed == 100 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"removed == 100\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                439 as ::core::ffi::c_uint,
                b"void test_set_iterating_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if set_num_entries(set) == (10000 as ::core::ffi::c_uint).wrapping_sub(removed) {
        } else {
            __assert_fail(
                b"set_num_entries(set) == 10000 - removed\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                440 as ::core::ffi::c_uint,
                b"void test_set_iterating_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set);
}
#[no_mangle]
pub unsafe extern "C" fn new_value(mut value: ::core::ffi::c_int) -> *mut ::core::ffi::c_int {
    let mut result: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    result = alloc_test_malloc(::core::mem::size_of::<::core::ffi::c_int>() as size_t)
        as *mut ::core::ffi::c_int;
    *result = value;
    allocated_values += 1;
    return result;
}
#[no_mangle]
pub unsafe extern "C" fn free_value(mut value: *mut ::core::ffi::c_void) {
    alloc_test_free(value);
    allocated_values -= 1;
}
#[no_mangle]
pub unsafe extern "C" fn test_set_free_function() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut i: ::core::ffi::c_int = 0;
    let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    set = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    set_register_free_function(
        set,
        Some(free_value as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ()),
    );
    allocated_values = 0 as ::core::ffi::c_int;
    i = 0 as ::core::ffi::c_int;
    while i < 1000 as ::core::ffi::c_int {
        value = new_value(i);
        set_insert(set, value as SetValue);
        i += 1;
    }
    '_c2rust_label: {
        if allocated_values == 1000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_values == 1000\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                484 as ::core::ffi::c_uint,
                b"void test_set_free_function(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 500 as ::core::ffi::c_int;
    set_remove(set, &raw mut i as SetValue);
    '_c2rust_label_0: {
        if allocated_values == 999 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_values == 999\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                491 as ::core::ffi::c_uint,
                b"void test_set_free_function(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set);
    '_c2rust_label_1: {
        if allocated_values == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_values == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                497 as ::core::ffi::c_uint,
                b"void test_set_free_function(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_set_out_of_memory() {
    let mut set: *mut Set = ::core::ptr::null_mut::<Set>();
    let mut values: [::core::ffi::c_int; 66] = [0; 66];
    let mut i: ::core::ffi::c_uint = 0;
    set = set_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    values[0 as ::core::ffi::c_int as usize] = 0 as ::core::ffi::c_int;
    '_c2rust_label: {
        if set_insert(
            set,
            (&raw mut values as *mut ::core::ffi::c_int).offset(0 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as SetValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"set_insert(set, &values[0]) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                514 as ::core::ffi::c_uint,
                b"void test_set_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if set_num_entries(set) == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"set_num_entries(set) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                515 as ::core::ffi::c_uint,
                b"void test_set_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(-(1 as ::core::ffi::c_int));
    i = 0 as ::core::ffi::c_uint;
    while i < 65 as ::core::ffi::c_uint {
        values[i as usize] = i as ::core::ffi::c_int;
        '_c2rust_label_1: {
            if set_insert(
                set,
                (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as SetValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"set_insert(set, &values[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    527 as ::core::ffi::c_uint,
                    b"void test_set_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_2: {
            if set_num_entries(set) == i.wrapping_add(1 as ::core::ffi::c_uint) {
            } else {
                __assert_fail(
                    b"set_num_entries(set) == i + 1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    528 as ::core::ffi::c_uint,
                    b"void test_set_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    '_c2rust_label_3: {
        if set_num_entries(set) == 65 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"set_num_entries(set) == 65\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                531 as ::core::ffi::c_uint,
                b"void test_set_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    values[65 as ::core::ffi::c_int as usize] = 65 as ::core::ffi::c_int;
    '_c2rust_label_4: {
        if set_insert(
            set,
            (&raw mut values as *mut ::core::ffi::c_int).offset(65 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as SetValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"set_insert(set, &values[65]) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                539 as ::core::ffi::c_uint,
                b"void test_set_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if set_num_entries(set) == 65 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"set_num_entries(set) == 65\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-set.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                540 as ::core::ffi::c_uint,
                b"void test_set_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    set_free(set);
}
static mut tests: [UnitTestFunction; 12] = unsafe {
    [
        Some(test_set_new_free as unsafe extern "C" fn() -> ()),
        Some(test_set_insert as unsafe extern "C" fn() -> ()),
        Some(test_set_query as unsafe extern "C" fn() -> ()),
        Some(test_set_remove as unsafe extern "C" fn() -> ()),
        Some(test_set_intersection as unsafe extern "C" fn() -> ()),
        Some(test_set_union as unsafe extern "C" fn() -> ()),
        Some(test_set_iterating as unsafe extern "C" fn() -> ()),
        Some(test_set_iterating_remove as unsafe extern "C" fn() -> ()),
        Some(test_set_to_array as unsafe extern "C" fn() -> ()),
        Some(test_set_free_function as unsafe extern "C" fn() -> ()),
        Some(test_set_out_of_memory as unsafe extern "C" fn() -> ()),
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
