extern "C" {
    pub type _BinaryHeap;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn binary_heap_new(
        heap_type: BinaryHeapType,
        compare_func: BinaryHeapCompareFunc,
    ) -> *mut BinaryHeap;
    fn binary_heap_free(heap: *mut BinaryHeap);
    fn binary_heap_insert(heap: *mut BinaryHeap, value: BinaryHeapValue) -> ::core::ffi::c_int;
    fn binary_heap_pop(heap: *mut BinaryHeap) -> BinaryHeapValue;
    fn binary_heap_num_entries(heap: *mut BinaryHeap) -> ::core::ffi::c_uint;
    fn int_compare(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
}
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type BinaryHeapType = ::core::ffi::c_uint;
pub const BINARY_HEAP_TYPE_MAX: BinaryHeapType = 1;
pub const BINARY_HEAP_TYPE_MIN: BinaryHeapType = 0;
pub type BinaryHeapValue = *mut ::core::ffi::c_void;
pub type BinaryHeapCompareFunc =
    Option<unsafe extern "C" fn(BinaryHeapValue, BinaryHeapValue) -> ::core::ffi::c_int>;
pub type BinaryHeap = _BinaryHeap;
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
pub const NUM_TEST_VALUES: ::core::ffi::c_int = 10000 as ::core::ffi::c_int;
#[no_mangle]
pub static mut test_array: [::core::ffi::c_int; 10000] = [0; 10000];
#[no_mangle]
pub unsafe extern "C" fn test_binary_heap_new_free() {
    let mut heap: *mut BinaryHeap = ::core::ptr::null_mut::<BinaryHeap>();
    let mut i: ::core::ffi::c_int = 0;
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        heap = binary_heap_new(
            BINARY_HEAP_TYPE_MIN,
            Some(
                int_compare
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
        );
        binary_heap_free(heap);
        i += 1;
    }
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    heap = binary_heap_new(
        BINARY_HEAP_TYPE_MIN,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label: {
        if heap.is_null() {
        } else {
            __assert_fail(
                b"heap == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                48 as ::core::ffi::c_uint,
                b"void test_binary_heap_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(1 as ::core::ffi::c_int);
    heap = binary_heap_new(
        BINARY_HEAP_TYPE_MIN,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_0: {
        if heap.is_null() {
        } else {
            __assert_fail(
                b"heap == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                52 as ::core::ffi::c_uint,
                b"void test_binary_heap_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_binary_heap_insert() {
    let mut heap: *mut BinaryHeap = ::core::ptr::null_mut::<BinaryHeap>();
    let mut i: ::core::ffi::c_int = 0;
    heap = binary_heap_new(
        BINARY_HEAP_TYPE_MIN,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        test_array[i as usize] = i;
        '_c2rust_label: {
            if binary_heap_insert(
                heap,
                (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as BinaryHeapValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binary_heap_insert(heap, &test_array[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    64 as ::core::ffi::c_uint,
                    b"void test_binary_heap_insert(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    '_c2rust_label_0: {
        if binary_heap_num_entries(heap) == 10000 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"binary_heap_num_entries(heap) == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                67 as ::core::ffi::c_uint,
                b"void test_binary_heap_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    binary_heap_free(heap);
}
#[no_mangle]
pub unsafe extern "C" fn test_min_heap() {
    let mut heap: *mut BinaryHeap = ::core::ptr::null_mut::<BinaryHeap>();
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    heap = binary_heap_new(
        BINARY_HEAP_TYPE_MIN,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        test_array[i as usize] = i;
        '_c2rust_label: {
            if binary_heap_insert(
                heap,
                (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as BinaryHeapValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binary_heap_insert(heap, &test_array[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    84 as ::core::ffi::c_uint,
                    b"void test_min_heap(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    i = -(1 as ::core::ffi::c_int);
    while binary_heap_num_entries(heap) > 0 as ::core::ffi::c_uint {
        val = binary_heap_pop(heap) as *mut ::core::ffi::c_int;
        '_c2rust_label_0: {
            if *val == i + 1 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"*val == i + 1\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    93 as ::core::ffi::c_uint,
                    b"void test_min_heap(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = *val;
    }
    '_c2rust_label_1: {
        if binary_heap_num_entries(heap) == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"binary_heap_num_entries(heap) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                99 as ::core::ffi::c_uint,
                b"void test_min_heap(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if binary_heap_pop(heap).is_null() {
        } else {
            __assert_fail(
                b"binary_heap_pop(heap) == BINARY_HEAP_NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                100 as ::core::ffi::c_uint,
                b"void test_min_heap(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    binary_heap_free(heap);
}
#[no_mangle]
pub unsafe extern "C" fn test_max_heap() {
    let mut heap: *mut BinaryHeap = ::core::ptr::null_mut::<BinaryHeap>();
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    heap = binary_heap_new(
        BINARY_HEAP_TYPE_MAX,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        test_array[i as usize] = i;
        '_c2rust_label: {
            if binary_heap_insert(
                heap,
                (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as BinaryHeapValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binary_heap_insert(heap, &test_array[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    117 as ::core::ffi::c_uint,
                    b"void test_max_heap(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    i = NUM_TEST_VALUES;
    while binary_heap_num_entries(heap) > 0 as ::core::ffi::c_uint {
        val = binary_heap_pop(heap) as *mut ::core::ffi::c_int;
        '_c2rust_label_0: {
            if *val == i - 1 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"*val == i - 1\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    126 as ::core::ffi::c_uint,
                    b"void test_max_heap(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = *val;
    }
    binary_heap_free(heap);
}
#[no_mangle]
pub unsafe extern "C" fn test_out_of_memory() {
    let mut heap: *mut BinaryHeap = ::core::ptr::null_mut::<BinaryHeap>();
    let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut values: [::core::ffi::c_int; 16] = [
        15 as ::core::ffi::c_int,
        14 as ::core::ffi::c_int,
        13 as ::core::ffi::c_int,
        12 as ::core::ffi::c_int,
        11 as ::core::ffi::c_int,
        10 as ::core::ffi::c_int,
        9 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        7 as ::core::ffi::c_int,
        6 as ::core::ffi::c_int,
        5 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        3 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        1 as ::core::ffi::c_int,
        0 as ::core::ffi::c_int,
    ];
    let mut i: ::core::ffi::c_int = 0;
    heap = binary_heap_new(
        BINARY_HEAP_TYPE_MIN,
        Some(
            int_compare
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    i = 0 as ::core::ffi::c_int;
    while i < 16 as ::core::ffi::c_int {
        '_c2rust_label: {
            if binary_heap_insert(
                heap,
                (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as BinaryHeapValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binary_heap_insert(heap, &values[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    151 as ::core::ffi::c_uint,
                    b"void test_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    '_c2rust_label_0: {
        if binary_heap_num_entries(heap) == 16 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"binary_heap_num_entries(heap) == 16\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                154 as ::core::ffi::c_uint,
                b"void test_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < 16 as ::core::ffi::c_int {
        '_c2rust_label_1: {
            if binary_heap_insert(
                heap,
                (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as BinaryHeapValue,
            ) == 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binary_heap_insert(heap, &values[i]) == 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    159 as ::core::ffi::c_uint,
                    b"void test_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_2: {
            if binary_heap_num_entries(heap) == 16 as ::core::ffi::c_uint {
            } else {
                __assert_fail(
                    b"binary_heap_num_entries(heap) == 16\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    160 as ::core::ffi::c_uint,
                    b"void test_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    i = 0 as ::core::ffi::c_int;
    while i < 16 as ::core::ffi::c_int {
        value = binary_heap_pop(heap) as *mut ::core::ffi::c_int;
        '_c2rust_label_3: {
            if *value == i {
            } else {
                __assert_fail(
                    b"*value == i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    168 as ::core::ffi::c_uint,
                    b"void test_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    '_c2rust_label_4: {
        if binary_heap_num_entries(heap) == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"binary_heap_num_entries(heap) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binary-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                171 as ::core::ffi::c_uint,
                b"void test_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    binary_heap_free(heap);
}
static mut tests: [UnitTestFunction; 6] = unsafe {
    [
        Some(test_binary_heap_new_free as unsafe extern "C" fn() -> ()),
        Some(test_binary_heap_insert as unsafe extern "C" fn() -> ()),
        Some(test_min_heap as unsafe extern "C" fn() -> ()),
        Some(test_max_heap as unsafe extern "C" fn() -> ()),
        Some(test_out_of_memory as unsafe extern "C" fn() -> ()),
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
