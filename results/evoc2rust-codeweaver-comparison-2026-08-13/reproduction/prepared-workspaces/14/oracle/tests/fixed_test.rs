extern "C" {
    pub type _SortedArray;
    fn rand() -> ::core::ffi::c_int;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn int_equal(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn int_compare(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn sortedarray_get(array: *mut SortedArray, i: ::core::ffi::c_uint) -> *mut SortedArrayValue;
    fn sortedarray_length(array: *mut SortedArray) -> ::core::ffi::c_uint;
    fn sortedarray_new(
        length: ::core::ffi::c_uint,
        equ_func: SortedArrayEqualFunc,
        cmp_func: SortedArrayCompareFunc,
    ) -> *mut SortedArray;
    fn sortedarray_free(sortedarray: *mut SortedArray);
    fn sortedarray_remove(sortedarray: *mut SortedArray, index: ::core::ffi::c_uint);
    fn sortedarray_remove_range(
        sortedarray: *mut SortedArray,
        index: ::core::ffi::c_uint,
        length: ::core::ffi::c_uint,
    );
    fn sortedarray_insert(
        sortedarray: *mut SortedArray,
        data: SortedArrayValue,
    ) -> ::core::ffi::c_int;
    fn sortedarray_index_of(
        sortedarray: *mut SortedArray,
        data: SortedArrayValue,
    ) -> ::core::ffi::c_int;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type SortedArrayValue = *mut ::core::ffi::c_void;
pub type SortedArray = _SortedArray;
pub type SortedArrayEqualFunc =
    Option<unsafe extern "C" fn(SortedArrayValue, SortedArrayValue) -> ::core::ffi::c_int>;
pub type SortedArrayCompareFunc =
    Option<unsafe extern "C" fn(SortedArrayValue, SortedArrayValue) -> ::core::ffi::c_int>;
pub const RAND_MAX: ::core::ffi::c_int = 2147483647 as ::core::ffi::c_int;
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
pub const TEST_SIZE: ::core::ffi::c_int = 20 as ::core::ffi::c_int;
pub const TEST_REMOVE_EL: ::core::ffi::c_int = 15 as ::core::ffi::c_int;
pub const TEST_REMOVE_RANGE: ::core::ffi::c_int = 7 as ::core::ffi::c_int;
pub const TEST_REMOVE_RANGE_LENGTH: ::core::ffi::c_int = 4 as ::core::ffi::c_int;
#[no_mangle]
pub unsafe extern "C" fn check_sorted_prop(mut sortedarray: *mut SortedArray) {
    let mut i: ::core::ffi::c_uint = 0;
    i = 1 as ::core::ffi::c_uint;
    while i < sortedarray_length(sortedarray) {
        '_c2rust_label: {
            if int_compare(
                sortedarray_get(sortedarray, i.wrapping_sub(1 as ::core::ffi::c_uint))
                    as *mut ::core::ffi::c_void,
                sortedarray_get(sortedarray, i) as *mut ::core::ffi::c_void,
            ) <= 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"int_compare( sortedarray_get(sortedarray, i-1), sortedarray_get(sortedarray, i)) <= 0\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    45 as ::core::ffi::c_uint,
                    b"void check_sorted_prop(SortedArray *)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
}
#[no_mangle]
pub unsafe extern "C" fn free_sorted_ints(mut sortedarray: *mut SortedArray) {
    let mut i: ::core::ffi::c_uint = 0;
    i = 0 as ::core::ffi::c_uint;
    while i < sortedarray_length(sortedarray) {
        let mut pi: *mut ::core::ffi::c_int =
            sortedarray_get(sortedarray, i) as *mut ::core::ffi::c_int;
        alloc_test_free(pi as *mut ::core::ffi::c_void);
        i = i.wrapping_add(1);
    }
    sortedarray_free(sortedarray);
}
#[no_mangle]
pub unsafe extern "C" fn generate_sortedarray_equ(
    mut equ_func: SortedArrayEqualFunc,
) -> *mut SortedArray {
    let mut sortedarray: *mut SortedArray = ::core::ptr::null_mut::<SortedArray>();
    let mut i: ::core::ffi::c_uint = 0;
    let mut array: [::core::ffi::c_int; 20] = [
        10 as ::core::ffi::c_int,
        12 as ::core::ffi::c_int,
        12 as ::core::ffi::c_int,
        1 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        3 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        23 as ::core::ffi::c_int,
        13 as ::core::ffi::c_int,
        23 as ::core::ffi::c_int,
        23 as ::core::ffi::c_int,
        34 as ::core::ffi::c_int,
        31 as ::core::ffi::c_int,
        9 as ::core::ffi::c_int,
        21 as ::core::ffi::c_int,
        -(2 as ::core::ffi::c_int),
        -(12 as ::core::ffi::c_int),
        -(4 as ::core::ffi::c_int),
    ];
    sortedarray = sortedarray_new(
        0 as ::core::ffi::c_uint,
        equ_func,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_uint;
    while i < TEST_SIZE as ::core::ffi::c_uint {
        let mut pi: *mut ::core::ffi::c_int = alloc_test_malloc(::core::mem::size_of::<
            ::core::ffi::c_int,
        >() as size_t) as *mut ::core::ffi::c_int;
        *pi = array[i as usize];
        sortedarray_insert(sortedarray, pi as SortedArrayValue);
        i = i.wrapping_add(1);
    }
    return sortedarray;
}
#[no_mangle]
pub unsafe extern "C" fn generate_sortedarray() -> *mut SortedArray {
    return generate_sortedarray_equ(Some(
        int_equal
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    ));
}
#[no_mangle]
pub unsafe extern "C" fn test_sortedarray_new_free() {
    let mut sortedarray: *mut SortedArray = ::core::ptr::null_mut::<SortedArray>();
    sortedarray = sortedarray_new(
        0 as ::core::ffi::c_uint,
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label: {
        if !sortedarray.is_null() {
        } else {
            __assert_fail(
                b"sortedarray != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                91 as ::core::ffi::c_uint,
                b"void test_sortedarray_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    sortedarray_free(sortedarray);
    sortedarray_free(::core::ptr::null_mut::<SortedArray>());
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    sortedarray = sortedarray_new(
        0 as ::core::ffi::c_uint,
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_0: {
        if sortedarray.is_null() {
        } else {
            __assert_fail(
                b"sortedarray == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                100 as ::core::ffi::c_uint,
                b"void test_sortedarray_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(-(1 as ::core::ffi::c_int));
}
#[no_mangle]
pub unsafe extern "C" fn test_sortedarray_insert() {
    let mut sortedarray: *mut SortedArray = generate_sortedarray();
    let mut i: ::core::ffi::c_uint = 0;
    i = 0 as ::core::ffi::c_uint;
    while i < 20 as ::core::ffi::c_uint {
        let mut i_0: ::core::ffi::c_int = (rand() as ::core::ffi::c_float
            / RAND_MAX as ::core::ffi::c_float
            * 100 as ::core::ffi::c_int as ::core::ffi::c_float)
            as ::core::ffi::c_int;
        let mut pi: *mut ::core::ffi::c_int = alloc_test_malloc(::core::mem::size_of::<
            ::core::ffi::c_int,
        >() as size_t) as *mut ::core::ffi::c_int;
        *pi = i_0;
        sortedarray_insert(sortedarray, pi as SortedArrayValue);
        i = i.wrapping_add(1);
    }
    check_sorted_prop(sortedarray);
    free_sorted_ints(sortedarray);
}
#[no_mangle]
pub unsafe extern "C" fn test_sortedarray_remove() {
    let mut sortedarray: *mut SortedArray = generate_sortedarray();
    let mut ip: *mut ::core::ffi::c_int = sortedarray_get(
        sortedarray,
        (TEST_REMOVE_EL + 1 as ::core::ffi::c_int) as ::core::ffi::c_uint,
    ) as *mut ::core::ffi::c_int;
    let mut i: ::core::ffi::c_int = *ip;
    alloc_test_free(
        sortedarray_get(sortedarray, TEST_REMOVE_EL as ::core::ffi::c_uint)
            as *mut ::core::ffi::c_int as *mut ::core::ffi::c_void,
    );
    sortedarray_remove(sortedarray, TEST_REMOVE_EL as ::core::ffi::c_uint);
    '_c2rust_label: {
        if *(sortedarray_get(sortedarray, 15 as ::core::ffi::c_uint) as *mut ::core::ffi::c_int)
            == i
        {
        } else {
            __assert_fail(
                b"*((int*) sortedarray_get(sortedarray, TEST_REMOVE_EL)) == i\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                131 as ::core::ffi::c_uint,
                b"void test_sortedarray_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    check_sorted_prop(sortedarray);
    free_sorted_ints(sortedarray);
}
#[no_mangle]
pub unsafe extern "C" fn test_sortedarray_remove_range() {
    let mut sortedarray: *mut SortedArray = generate_sortedarray();
    let mut new: [::core::ffi::c_int; 4] = [0; 4];
    let mut i: ::core::ffi::c_uint = 0;
    i = 0 as ::core::ffi::c_uint;
    while i < TEST_REMOVE_RANGE_LENGTH as ::core::ffi::c_uint {
        new[i as usize] = *(sortedarray_get(
            sortedarray,
            ((TEST_REMOVE_RANGE + TEST_REMOVE_RANGE_LENGTH) as ::core::ffi::c_uint).wrapping_add(i),
        ) as *mut ::core::ffi::c_int);
        i = i.wrapping_add(1);
    }
    i = 0 as ::core::ffi::c_uint;
    while i < TEST_REMOVE_RANGE_LENGTH as ::core::ffi::c_uint {
        alloc_test_free(sortedarray_get(
            sortedarray,
            (TEST_REMOVE_RANGE as ::core::ffi::c_uint).wrapping_add(i),
        ) as *mut ::core::ffi::c_int
            as *mut ::core::ffi::c_void);
        i = i.wrapping_add(1);
    }
    sortedarray_remove_range(
        sortedarray,
        TEST_REMOVE_RANGE as ::core::ffi::c_uint,
        TEST_REMOVE_RANGE_LENGTH as ::core::ffi::c_uint,
    );
    i = 0 as ::core::ffi::c_uint;
    while i < TEST_REMOVE_RANGE_LENGTH as ::core::ffi::c_uint {
        '_c2rust_label: {
            if *(sortedarray_get(sortedarray, (7 as ::core::ffi::c_uint).wrapping_add(i))
                as *mut ::core::ffi::c_int)
                == new[i as usize]
            {
            } else {
                __assert_fail(
                    b"*((int*) sortedarray_get(sortedarray, TEST_REMOVE_RANGE + i)) == new[i]\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    161 as ::core::ffi::c_uint,
                    b"void test_sortedarray_remove_range(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    check_sorted_prop(sortedarray);
    free_sorted_ints(sortedarray);
}
#[no_mangle]
pub unsafe extern "C" fn test_sortedarray_index_of() {
    let mut sortedarray: *mut SortedArray = generate_sortedarray();
    let mut i: ::core::ffi::c_uint = 0;
    i = 0 as ::core::ffi::c_uint;
    while i < TEST_SIZE as ::core::ffi::c_uint {
        let mut r: ::core::ffi::c_int = sortedarray_index_of(
            sortedarray,
            sortedarray_get(sortedarray, i) as SortedArrayValue,
        );
        '_c2rust_label: {
            if r >= 0 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"r >= 0\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    175 as ::core::ffi::c_uint,
                    b"void test_sortedarray_index_of(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_0: {
            if *(sortedarray_get(sortedarray, r as ::core::ffi::c_uint) as *mut ::core::ffi::c_int)
                == *(sortedarray_get(sortedarray, i) as *mut ::core::ffi::c_int)
            {
            } else {
                __assert_fail(
                    b"*((int*) sortedarray_get(sortedarray,(unsigned int) r)) == *((int*) sortedarray_get(sortedarray, i))\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    177 as ::core::ffi::c_uint,
                    b"void test_sortedarray_index_of(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    free_sorted_ints(sortedarray);
}
unsafe extern "C" fn ptr_equal(
    mut v1: SortedArrayValue,
    mut v2: SortedArrayValue,
) -> ::core::ffi::c_int {
    return (v1 == v2) as ::core::ffi::c_int;
}
#[no_mangle]
pub unsafe extern "C" fn test_sortedarray_index_of_equ_key() {
    let mut sortedarray: *mut SortedArray = generate_sortedarray_equ(Some(
        ptr_equal as unsafe extern "C" fn(SortedArrayValue, SortedArrayValue) -> ::core::ffi::c_int,
    ));
    let mut i: ::core::ffi::c_uint = 0;
    i = 0 as ::core::ffi::c_uint;
    while i < TEST_SIZE as ::core::ffi::c_uint {
        let mut r: ::core::ffi::c_int = sortedarray_index_of(
            sortedarray,
            sortedarray_get(sortedarray, i) as SortedArrayValue,
        );
        '_c2rust_label: {
            if r >= 0 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"r >= 0\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    197 as ::core::ffi::c_uint,
                    b"void test_sortedarray_index_of_equ_key(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_0: {
            if i == r as ::core::ffi::c_uint {
            } else {
                __assert_fail(
                    b"i == (unsigned int) r\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    198 as ::core::ffi::c_uint,
                    b"void test_sortedarray_index_of_equ_key(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    free_sorted_ints(sortedarray);
}
#[no_mangle]
pub unsafe extern "C" fn test_sortedarray_get() {
    let mut i: ::core::ffi::c_uint = 0;
    let mut arr: *mut SortedArray = generate_sortedarray();
    i = 0 as ::core::ffi::c_uint;
    while i < sortedarray_length(arr) {
        '_c2rust_label: {
            if sortedarray_get(arr, i) == sortedarray_get(arr, i) {
            } else {
                __assert_fail(
                    b"sortedarray_get(arr, i) == sortedarray_get(arr, i)\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    210 as ::core::ffi::c_uint,
                    b"void test_sortedarray_get(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_0: {
            if *(sortedarray_get(arr, i) as *mut ::core::ffi::c_int)
                == *(sortedarray_get(arr, i) as *mut ::core::ffi::c_int)
            {
            } else {
                __assert_fail(
                    b"*((int*) sortedarray_get(arr, i)) == *((int*) sortedarray_get(arr, i))\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-sortedarray.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    212 as ::core::ffi::c_uint,
                    b"void test_sortedarray_get(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    free_sorted_ints(arr);
}
static mut tests: [UnitTestFunction; 8] = unsafe {
    [
        Some(test_sortedarray_new_free as unsafe extern "C" fn() -> ()),
        Some(test_sortedarray_insert as unsafe extern "C" fn() -> ()),
        Some(test_sortedarray_remove as unsafe extern "C" fn() -> ()),
        Some(test_sortedarray_remove_range as unsafe extern "C" fn() -> ()),
        Some(test_sortedarray_index_of as unsafe extern "C" fn() -> ()),
        Some(test_sortedarray_index_of_equ_key as unsafe extern "C" fn() -> ()),
        Some(test_sortedarray_get as unsafe extern "C" fn() -> ()),
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
