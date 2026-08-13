extern "C" {
    pub type _Queue;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn queue_new() -> *mut Queue;
    fn queue_free(queue: *mut Queue);
    fn queue_push_head(queue: *mut Queue, data: QueueValue) -> ::core::ffi::c_int;
    fn queue_pop_head(queue: *mut Queue) -> QueueValue;
    fn queue_peek_head(queue: *mut Queue) -> QueueValue;
    fn queue_push_tail(queue: *mut Queue, data: QueueValue) -> ::core::ffi::c_int;
    fn queue_pop_tail(queue: *mut Queue) -> QueueValue;
    fn queue_peek_tail(queue: *mut Queue) -> QueueValue;
    fn queue_is_empty(queue: *mut Queue) -> ::core::ffi::c_int;
}
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type Queue = _Queue;
pub type QueueValue = *mut ::core::ffi::c_void;
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
pub unsafe extern "C" fn generate_queue() -> *mut Queue {
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    let mut i: ::core::ffi::c_int = 0;
    queue = queue_new();
    i = 0 as ::core::ffi::c_int;
    while i < 1000 as ::core::ffi::c_int {
        queue_push_head(queue, &raw mut variable1 as QueueValue);
        queue_push_head(queue, &raw mut variable2 as QueueValue);
        queue_push_head(queue, &raw mut variable3 as QueueValue);
        queue_push_head(queue, &raw mut variable4 as QueueValue);
        i += 1;
    }
    return queue;
}
#[no_mangle]
pub unsafe extern "C" fn test_queue_new_free() {
    let mut i: ::core::ffi::c_int = 0;
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    queue = queue_new();
    queue_free(queue);
    queue = queue_new();
    i = 0 as ::core::ffi::c_int;
    while i < 1000 as ::core::ffi::c_int {
        queue_push_head(queue, &raw mut variable1 as QueueValue);
        i += 1;
    }
    queue_free(queue);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    queue = queue_new();
    '_c2rust_label: {
        if queue.is_null() {
        } else {
            __assert_fail(
                b"queue == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                78 as ::core::ffi::c_uint,
                b"void test_queue_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_queue_push_head() {
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    let mut i: ::core::ffi::c_int = 0;
    queue = queue_new();
    i = 0 as ::core::ffi::c_int;
    while i < 1000 as ::core::ffi::c_int {
        queue_push_head(queue, &raw mut variable1 as QueueValue);
        queue_push_head(queue, &raw mut variable2 as QueueValue);
        queue_push_head(queue, &raw mut variable3 as QueueValue);
        queue_push_head(queue, &raw mut variable4 as QueueValue);
        i += 1;
    }
    '_c2rust_label: {
        if queue_is_empty(queue) == 0 {
        } else {
            __assert_fail(
                b"!queue_is_empty(queue)\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                97 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if queue_pop_tail(queue) == &raw mut variable1 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                101 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if queue_pop_tail(queue) == &raw mut variable2 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                102 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if queue_pop_tail(queue) == &raw mut variable3 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                103 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if queue_pop_tail(queue) == &raw mut variable4 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                104 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if queue_pop_head(queue) == &raw mut variable4 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                108 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if queue_pop_head(queue) == &raw mut variable3 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                109 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if queue_pop_head(queue) == &raw mut variable2 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                110 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if queue_pop_head(queue) == &raw mut variable1 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                111 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
    queue = queue_new();
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_8: {
        if queue_push_head(queue, &raw mut variable1 as QueueValue) == 0 {
        } else {
            __assert_fail(
                b"!queue_push_head(queue, &variable1)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                120 as ::core::ffi::c_uint,
                b"void test_queue_push_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
}
#[no_mangle]
pub unsafe extern "C" fn test_queue_pop_head() {
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    queue = queue_new();
    '_c2rust_label: {
        if queue_pop_head(queue).is_null() {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                133 as ::core::ffi::c_uint,
                b"void test_queue_pop_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
    queue = generate_queue();
    while queue_is_empty(queue) == 0 {
        '_c2rust_label_0: {
            if queue_pop_head(queue) == &raw mut variable4 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_head(queue) == &variable4\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    142 as ::core::ffi::c_uint,
                    b"void test_queue_pop_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_1: {
            if queue_pop_head(queue) == &raw mut variable3 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_head(queue) == &variable3\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    143 as ::core::ffi::c_uint,
                    b"void test_queue_pop_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_2: {
            if queue_pop_head(queue) == &raw mut variable2 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_head(queue) == &variable2\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    144 as ::core::ffi::c_uint,
                    b"void test_queue_pop_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_3: {
            if queue_pop_head(queue) == &raw mut variable1 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_head(queue) == &variable1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    145 as ::core::ffi::c_uint,
                    b"void test_queue_pop_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
    }
    '_c2rust_label_4: {
        if queue_pop_head(queue).is_null() {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                148 as ::core::ffi::c_uint,
                b"void test_queue_pop_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
}
#[no_mangle]
pub unsafe extern "C" fn test_queue_peek_head() {
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    queue = queue_new();
    '_c2rust_label: {
        if queue_peek_head(queue).is_null() {
        } else {
            __assert_fail(
                b"queue_peek_head(queue) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                161 as ::core::ffi::c_uint,
                b"void test_queue_peek_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
    queue = generate_queue();
    while queue_is_empty(queue) == 0 {
        '_c2rust_label_0: {
            if queue_peek_head(queue) == &raw mut variable4 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_peek_head(queue) == &variable4\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    171 as ::core::ffi::c_uint,
                    b"void test_queue_peek_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_1: {
            if queue_pop_head(queue) == &raw mut variable4 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_head(queue) == &variable4\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    172 as ::core::ffi::c_uint,
                    b"void test_queue_peek_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_2: {
            if queue_peek_head(queue) == &raw mut variable3 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_peek_head(queue) == &variable3\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    173 as ::core::ffi::c_uint,
                    b"void test_queue_peek_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_3: {
            if queue_pop_head(queue) == &raw mut variable3 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_head(queue) == &variable3\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    174 as ::core::ffi::c_uint,
                    b"void test_queue_peek_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_4: {
            if queue_peek_head(queue) == &raw mut variable2 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_peek_head(queue) == &variable2\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    175 as ::core::ffi::c_uint,
                    b"void test_queue_peek_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_5: {
            if queue_pop_head(queue) == &raw mut variable2 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_head(queue) == &variable2\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    176 as ::core::ffi::c_uint,
                    b"void test_queue_peek_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_6: {
            if queue_peek_head(queue) == &raw mut variable1 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_peek_head(queue) == &variable1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    177 as ::core::ffi::c_uint,
                    b"void test_queue_peek_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_7: {
            if queue_pop_head(queue) == &raw mut variable1 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_head(queue) == &variable1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    178 as ::core::ffi::c_uint,
                    b"void test_queue_peek_head(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
    }
    '_c2rust_label_8: {
        if queue_peek_head(queue).is_null() {
        } else {
            __assert_fail(
                b"queue_peek_head(queue) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                181 as ::core::ffi::c_uint,
                b"void test_queue_peek_head(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
}
#[no_mangle]
pub unsafe extern "C" fn test_queue_push_tail() {
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    let mut i: ::core::ffi::c_int = 0;
    queue = queue_new();
    i = 0 as ::core::ffi::c_int;
    while i < 1000 as ::core::ffi::c_int {
        queue_push_tail(queue, &raw mut variable1 as QueueValue);
        queue_push_tail(queue, &raw mut variable2 as QueueValue);
        queue_push_tail(queue, &raw mut variable3 as QueueValue);
        queue_push_tail(queue, &raw mut variable4 as QueueValue);
        i += 1;
    }
    '_c2rust_label: {
        if queue_is_empty(queue) == 0 {
        } else {
            __assert_fail(
                b"!queue_is_empty(queue)\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                202 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if queue_pop_head(queue) == &raw mut variable1 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                206 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if queue_pop_head(queue) == &raw mut variable2 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                207 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if queue_pop_head(queue) == &raw mut variable3 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                208 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if queue_pop_head(queue) == &raw mut variable4 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_head(queue) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                209 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if queue_pop_tail(queue) == &raw mut variable4 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == &variable4\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                213 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if queue_pop_tail(queue) == &raw mut variable3 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == &variable3\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                214 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if queue_pop_tail(queue) == &raw mut variable2 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == &variable2\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                215 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_7: {
        if queue_pop_tail(queue) == &raw mut variable1 as QueueValue {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == &variable1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                216 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
    queue = queue_new();
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    '_c2rust_label_8: {
        if queue_push_tail(queue, &raw mut variable1 as QueueValue) == 0 {
        } else {
            __assert_fail(
                b"!queue_push_tail(queue, &variable1)\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                225 as ::core::ffi::c_uint,
                b"void test_queue_push_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
}
#[no_mangle]
pub unsafe extern "C" fn test_queue_pop_tail() {
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    queue = queue_new();
    '_c2rust_label: {
        if queue_pop_tail(queue).is_null() {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                238 as ::core::ffi::c_uint,
                b"void test_queue_pop_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
    queue = generate_queue();
    while queue_is_empty(queue) == 0 {
        '_c2rust_label_0: {
            if queue_pop_tail(queue) == &raw mut variable1 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_tail(queue) == &variable1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    247 as ::core::ffi::c_uint,
                    b"void test_queue_pop_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_1: {
            if queue_pop_tail(queue) == &raw mut variable2 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_tail(queue) == &variable2\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    248 as ::core::ffi::c_uint,
                    b"void test_queue_pop_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_2: {
            if queue_pop_tail(queue) == &raw mut variable3 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_tail(queue) == &variable3\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    249 as ::core::ffi::c_uint,
                    b"void test_queue_pop_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_3: {
            if queue_pop_tail(queue) == &raw mut variable4 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_tail(queue) == &variable4\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    250 as ::core::ffi::c_uint,
                    b"void test_queue_pop_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
    }
    '_c2rust_label_4: {
        if queue_pop_tail(queue).is_null() {
        } else {
            __assert_fail(
                b"queue_pop_tail(queue) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                253 as ::core::ffi::c_uint,
                b"void test_queue_pop_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
}
#[no_mangle]
pub unsafe extern "C" fn test_queue_peek_tail() {
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    queue = queue_new();
    '_c2rust_label: {
        if queue_peek_tail(queue).is_null() {
        } else {
            __assert_fail(
                b"queue_peek_tail(queue) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                266 as ::core::ffi::c_uint,
                b"void test_queue_peek_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
    queue = generate_queue();
    while queue_is_empty(queue) == 0 {
        '_c2rust_label_0: {
            if queue_peek_tail(queue) == &raw mut variable1 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_peek_tail(queue) == &variable1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    276 as ::core::ffi::c_uint,
                    b"void test_queue_peek_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_1: {
            if queue_pop_tail(queue) == &raw mut variable1 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_tail(queue) == &variable1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    277 as ::core::ffi::c_uint,
                    b"void test_queue_peek_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_2: {
            if queue_peek_tail(queue) == &raw mut variable2 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_peek_tail(queue) == &variable2\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    278 as ::core::ffi::c_uint,
                    b"void test_queue_peek_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_3: {
            if queue_pop_tail(queue) == &raw mut variable2 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_tail(queue) == &variable2\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    279 as ::core::ffi::c_uint,
                    b"void test_queue_peek_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_4: {
            if queue_peek_tail(queue) == &raw mut variable3 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_peek_tail(queue) == &variable3\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    280 as ::core::ffi::c_uint,
                    b"void test_queue_peek_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_5: {
            if queue_pop_tail(queue) == &raw mut variable3 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_tail(queue) == &variable3\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    281 as ::core::ffi::c_uint,
                    b"void test_queue_peek_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_6: {
            if queue_peek_tail(queue) == &raw mut variable4 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_peek_tail(queue) == &variable4\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    282 as ::core::ffi::c_uint,
                    b"void test_queue_peek_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_7: {
            if queue_pop_tail(queue) == &raw mut variable4 as QueueValue {
            } else {
                __assert_fail(
                    b"queue_pop_tail(queue) == &variable4\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    283 as ::core::ffi::c_uint,
                    b"void test_queue_peek_tail(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
    }
    '_c2rust_label_8: {
        if queue_peek_tail(queue).is_null() {
        } else {
            __assert_fail(
                b"queue_peek_tail(queue) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                286 as ::core::ffi::c_uint,
                b"void test_queue_peek_tail(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
}
#[no_mangle]
pub unsafe extern "C" fn test_queue_is_empty() {
    let mut queue: *mut Queue = ::core::ptr::null_mut::<Queue>();
    queue = queue_new();
    '_c2rust_label: {
        if queue_is_empty(queue) != 0 {
        } else {
            __assert_fail(
                b"queue_is_empty(queue)\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                297 as ::core::ffi::c_uint,
                b"void test_queue_is_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_push_head(queue, &raw mut variable1 as QueueValue);
    '_c2rust_label_0: {
        if queue_is_empty(queue) == 0 {
        } else {
            __assert_fail(
                b"!queue_is_empty(queue)\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                301 as ::core::ffi::c_uint,
                b"void test_queue_is_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_pop_head(queue);
    '_c2rust_label_1: {
        if queue_is_empty(queue) != 0 {
        } else {
            __assert_fail(
                b"queue_is_empty(queue)\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                305 as ::core::ffi::c_uint,
                b"void test_queue_is_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_push_tail(queue, &raw mut variable1 as QueueValue);
    '_c2rust_label_2: {
        if queue_is_empty(queue) == 0 {
        } else {
            __assert_fail(
                b"!queue_is_empty(queue)\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                309 as ::core::ffi::c_uint,
                b"void test_queue_is_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_pop_tail(queue);
    '_c2rust_label_3: {
        if queue_is_empty(queue) != 0 {
        } else {
            __assert_fail(
                b"queue_is_empty(queue)\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-queue.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                313 as ::core::ffi::c_uint,
                b"void test_queue_is_empty(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    queue_free(queue);
}
static mut tests: [UnitTestFunction; 9] = unsafe {
    [
        Some(test_queue_new_free as unsafe extern "C" fn() -> ()),
        Some(test_queue_push_head as unsafe extern "C" fn() -> ()),
        Some(test_queue_pop_head as unsafe extern "C" fn() -> ()),
        Some(test_queue_peek_head as unsafe extern "C" fn() -> ()),
        Some(test_queue_push_tail as unsafe extern "C" fn() -> ()),
        Some(test_queue_pop_tail as unsafe extern "C" fn() -> ()),
        Some(test_queue_peek_tail as unsafe extern "C" fn() -> ()),
        Some(test_queue_is_empty as unsafe extern "C" fn() -> ()),
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
