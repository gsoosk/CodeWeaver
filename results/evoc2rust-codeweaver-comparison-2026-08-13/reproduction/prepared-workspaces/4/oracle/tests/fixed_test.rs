extern "C" {
    pub type _BinomialHeap;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn binomial_heap_new(
        heap_type: BinomialHeapType,
        compare_func: BinomialHeapCompareFunc,
    ) -> *mut BinomialHeap;
    fn binomial_heap_free(heap: *mut BinomialHeap);
    fn binomial_heap_insert(
        heap: *mut BinomialHeap,
        value: BinomialHeapValue,
    ) -> ::core::ffi::c_int;
    fn binomial_heap_pop(heap: *mut BinomialHeap) -> BinomialHeapValue;
    fn binomial_heap_num_entries(heap: *mut BinomialHeap) -> ::core::ffi::c_uint;
    fn int_compare(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
}
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type BinomialHeapType = ::core::ffi::c_uint;
pub const BINOMIAL_HEAP_TYPE_MAX: BinomialHeapType = 1;
pub const BINOMIAL_HEAP_TYPE_MIN: BinomialHeapType = 0;
pub type BinomialHeapValue = *mut ::core::ffi::c_void;
pub type BinomialHeapCompareFunc =
    Option<unsafe extern "C" fn(BinomialHeapValue, BinomialHeapValue) -> ::core::ffi::c_int>;
pub type BinomialHeap = _BinomialHeap;
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
pub unsafe extern "C" fn test_binomial_heap_new_free() {
    let mut heap: *mut BinomialHeap = ::core::ptr::null_mut::<BinomialHeap>();
    let mut i: ::core::ffi::c_int = 0;
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        heap = binomial_heap_new(
            BINOMIAL_HEAP_TYPE_MIN,
            Some(
                int_compare
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
        );
        binomial_heap_free(heap);
        i += 1;
    }
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label: {
        if binomial_heap_new(
            BINOMIAL_HEAP_TYPE_MIN,
            Some(
                int_compare
                    as unsafe extern "C" fn(
                        *mut ::core::ffi::c_void,
                        *mut ::core::ffi::c_void,
                    ) -> ::core::ffi::c_int,
            ),
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"binomial_heap_new(BINOMIAL_HEAP_TYPE_MIN, int_compare) == NULL\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                48 as ::core::ffi::c_uint,
                b"void test_binomial_heap_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_binomial_heap_insert() {
    let mut heap: *mut BinomialHeap = ::core::ptr::null_mut::<BinomialHeap>();
    let mut i: ::core::ffi::c_int = 0;
    heap = binomial_heap_new(
        BINOMIAL_HEAP_TYPE_MIN,
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
            if binomial_heap_insert(
                heap,
                (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as BinomialHeapValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binomial_heap_insert(heap, &test_array[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    60 as ::core::ffi::c_uint,
                    b"void test_binomial_heap_insert(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    '_c2rust_label_0: {
        if binomial_heap_num_entries(heap) == 10000 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"binomial_heap_num_entries(heap) == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                62 as ::core::ffi::c_uint,
                b"void test_binomial_heap_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_1: {
        if binomial_heap_insert(heap, &raw mut i as BinomialHeapValue) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"binomial_heap_insert(heap, &i) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                67 as ::core::ffi::c_uint,
                b"void test_binomial_heap_insert(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    binomial_heap_free(heap);
}
#[no_mangle]
pub unsafe extern "C" fn test_min_heap() {
    let mut heap: *mut BinomialHeap = ::core::ptr::null_mut::<BinomialHeap>();
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    heap = binomial_heap_new(
        BINOMIAL_HEAP_TYPE_MIN,
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
            if binomial_heap_insert(
                heap,
                (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as BinomialHeapValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binomial_heap_insert(heap, &test_array[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
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
    while binomial_heap_num_entries(heap) > 0 as ::core::ffi::c_uint {
        val = binomial_heap_pop(heap) as *mut ::core::ffi::c_int;
        '_c2rust_label_0: {
            if *val == i + 1 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"*val == i + 1\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    93 as ::core::ffi::c_uint,
                    b"void test_min_heap(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = *val;
    }
    val = binomial_heap_pop(heap) as *mut ::core::ffi::c_int;
    '_c2rust_label_1: {
        if val.is_null() {
        } else {
            __assert_fail(
                b"val == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                100 as ::core::ffi::c_uint,
                b"void test_min_heap(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    binomial_heap_free(heap);
}
#[no_mangle]
pub unsafe extern "C" fn test_max_heap() {
    let mut heap: *mut BinomialHeap = ::core::ptr::null_mut::<BinomialHeap>();
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    heap = binomial_heap_new(
        BINOMIAL_HEAP_TYPE_MAX,
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
            if binomial_heap_insert(
                heap,
                (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as BinomialHeapValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binomial_heap_insert(heap, &test_array[i]) != 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
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
    while binomial_heap_num_entries(heap) > 0 as ::core::ffi::c_uint {
        val = binomial_heap_pop(heap) as *mut ::core::ffi::c_int;
        '_c2rust_label_0: {
            if *val == i - 1 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"*val == i - 1\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    126 as ::core::ffi::c_uint,
                    b"void test_max_heap(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = *val;
    }
    val = binomial_heap_pop(heap) as *mut ::core::ffi::c_int;
    '_c2rust_label_1: {
        if val.is_null() {
        } else {
            __assert_fail(
                b"val == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                133 as ::core::ffi::c_uint,
                b"void test_max_heap(void)\0" as *const u8 as *const ::core::ffi::c_char,
            );
        }
    };
    binomial_heap_free(heap);
}
pub const TEST_VALUE: ::core::ffi::c_int = NUM_TEST_VALUES / 2 as ::core::ffi::c_int;
unsafe extern "C" fn generate_heap() -> *mut BinomialHeap {
    let mut heap: *mut BinomialHeap = ::core::ptr::null_mut::<BinomialHeap>();
    let mut i: ::core::ffi::c_int = 0;
    heap = binomial_heap_new(
        BINOMIAL_HEAP_TYPE_MIN,
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
        if i != TEST_VALUE {
            '_c2rust_label: {
                if binomial_heap_insert(
                    heap,
                    (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                        as *mut ::core::ffi::c_int as BinomialHeapValue,
                ) != 0 as ::core::ffi::c_int
                {
                } else {
                    __assert_fail(
                        b"binomial_heap_insert(heap, &test_array[i]) != 0\0" as *const u8
                            as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        153 as ::core::ffi::c_uint,
                        b"BinomialHeap *generate_heap(void)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
        }
        i += 1;
    }
    return heap;
}
unsafe extern "C" fn verify_heap(mut heap: *mut BinomialHeap) {
    let mut num_vals: ::core::ffi::c_uint = 0;
    let mut val: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    num_vals = binomial_heap_num_entries(heap);
    '_c2rust_label: {
        if num_vals
            == (10000 as ::core::ffi::c_int - 1 as ::core::ffi::c_int) as ::core::ffi::c_uint
        {
        } else {
            __assert_fail(
                b"num_vals == NUM_TEST_VALUES - 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                170 as ::core::ffi::c_uint,
                b"void verify_heap(BinomialHeap *)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        if !(i == TEST_VALUE) {
            val = binomial_heap_pop(heap) as *mut ::core::ffi::c_int;
            '_c2rust_label_0: {
                if *val == i {
                } else {
                    __assert_fail(
                        b"*val == i\0" as *const u8 as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        180 as ::core::ffi::c_uint,
                        b"void verify_heap(BinomialHeap *)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
            num_vals = num_vals.wrapping_sub(1);
            '_c2rust_label_1: {
                if binomial_heap_num_entries(heap) == num_vals {
                } else {
                    __assert_fail(
                        b"binomial_heap_num_entries(heap) == num_vals\0" as *const u8
                            as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        185 as ::core::ffi::c_uint,
                        b"void verify_heap(BinomialHeap *)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
        }
        i += 1;
    }
}
unsafe extern "C" fn test_insert_out_of_memory() {
    let mut heap: *mut BinomialHeap = ::core::ptr::null_mut::<BinomialHeap>();
    let mut i: ::core::ffi::c_int = 0;
    i = 0 as ::core::ffi::c_int;
    while i < 6 as ::core::ffi::c_int {
        heap = generate_heap();
        alloc_test_set_limit(i);
        test_array[TEST_VALUE as usize] = TEST_VALUE;
        '_c2rust_label: {
            if binomial_heap_insert(
                heap,
                (&raw mut test_array as *mut ::core::ffi::c_int)
                    .offset((10000 as ::core::ffi::c_int / 2 as ::core::ffi::c_int) as isize)
                    as *mut ::core::ffi::c_int as BinomialHeapValue,
            ) == 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"binomial_heap_insert(heap, &test_array[TEST_VALUE]) == 0\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    207 as ::core::ffi::c_uint,
                    b"void test_insert_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        alloc_test_set_limit(-(1 as ::core::ffi::c_int));
        verify_heap(heap);
        binomial_heap_free(heap);
        i += 1;
    }
}
#[no_mangle]
pub unsafe extern "C" fn test_pop_out_of_memory() {
    let mut heap: *mut BinomialHeap = ::core::ptr::null_mut::<BinomialHeap>();
    let mut i: ::core::ffi::c_int = 0;
    i = 0 as ::core::ffi::c_int;
    while i < 6 as ::core::ffi::c_int {
        heap = generate_heap();
        alloc_test_set_limit(i);
        '_c2rust_label: {
            if binomial_heap_pop(heap).is_null() {
            } else {
                __assert_fail(
                    b"binomial_heap_pop(heap) == NULL\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-binomial-heap.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    235 as ::core::ffi::c_uint,
                    b"void test_pop_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        alloc_test_set_limit(-(1 as ::core::ffi::c_int));
        binomial_heap_free(heap);
        i += 1;
    }
}
static mut tests: [UnitTestFunction; 7] = unsafe {
    [
        Some(test_binomial_heap_new_free as unsafe extern "C" fn() -> ()),
        Some(test_binomial_heap_insert as unsafe extern "C" fn() -> ()),
        Some(test_min_heap as unsafe extern "C" fn() -> ()),
        Some(test_max_heap as unsafe extern "C" fn() -> ()),
        Some(test_insert_out_of_memory as unsafe extern "C" fn() -> ()),
        Some(test_pop_out_of_memory as unsafe extern "C" fn() -> ()),
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
