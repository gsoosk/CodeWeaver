extern "C" {
    pub type _HashTable;
    pub type _HashTableEntry;
    fn sprintf(
        __s: *mut ::core::ffi::c_char,
        __format: *const ::core::ffi::c_char,
        ...
    ) -> ::core::ffi::c_int;
    fn atoi(__nptr: *const ::core::ffi::c_char) -> ::core::ffi::c_int;
    fn strcmp(
        __s1: *const ::core::ffi::c_char,
        __s2: *const ::core::ffi::c_char,
    ) -> ::core::ffi::c_int;
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
    fn hash_table_new(
        hash_func: HashTableHashFunc,
        equal_func: HashTableEqualFunc,
    ) -> *mut HashTable;
    fn hash_table_free(hash_table: *mut HashTable);
    fn hash_table_register_free_functions(
        hash_table: *mut HashTable,
        key_free_func: HashTableKeyFreeFunc,
        value_free_func: HashTableValueFreeFunc,
    );
    fn hash_table_insert(
        hash_table: *mut HashTable,
        key: HashTableKey,
        value: HashTableValue,
    ) -> ::core::ffi::c_int;
    fn hash_table_lookup(hash_table: *mut HashTable, key: HashTableKey) -> HashTableValue;
    fn hash_table_remove(hash_table: *mut HashTable, key: HashTableKey) -> ::core::ffi::c_int;
    fn hash_table_num_entries(hash_table: *mut HashTable) -> ::core::ffi::c_uint;
    fn hash_table_iterate(hash_table: *mut HashTable, iter: *mut HashTableIterator);
    fn hash_table_iter_has_more(iterator: *mut HashTableIterator) -> ::core::ffi::c_int;
    fn hash_table_iter_next(iterator: *mut HashTableIterator) -> HashTablePair;
    fn int_hash(location: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
    fn int_equal(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
    fn string_hash(string: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint;
    fn string_equal(
        string1: *mut ::core::ffi::c_void,
        string2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type HashTable = _HashTable;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _HashTableIterator {
    pub hash_table: *mut HashTable,
    pub next_entry: *mut HashTableEntry,
    pub next_chain: ::core::ffi::c_uint,
}
pub type HashTableEntry = _HashTableEntry;
pub type HashTableIterator = _HashTableIterator;
pub type HashTableKey = *mut ::core::ffi::c_void;
pub type HashTableValue = *mut ::core::ffi::c_void;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _HashTablePair {
    pub key: HashTableKey,
    pub value: HashTableValue,
}
pub type HashTablePair = _HashTablePair;
pub type HashTableHashFunc = Option<unsafe extern "C" fn(HashTableKey) -> ::core::ffi::c_uint>;
pub type HashTableEqualFunc =
    Option<unsafe extern "C" fn(HashTableKey, HashTableKey) -> ::core::ffi::c_int>;
pub type HashTableKeyFreeFunc = Option<unsafe extern "C" fn(HashTableKey) -> ()>;
pub type HashTableValueFreeFunc = Option<unsafe extern "C" fn(HashTableValue) -> ()>;
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
pub const NUM_TEST_VALUES: ::core::ffi::c_int = 10000 as ::core::ffi::c_int;
#[no_mangle]
pub static mut value3: ::core::ffi::c_int = 3 as ::core::ffi::c_int;
#[no_mangle]
pub static mut value1: ::core::ffi::c_int = 1 as ::core::ffi::c_int;
#[no_mangle]
pub static mut value2: ::core::ffi::c_int = 2 as ::core::ffi::c_int;
#[no_mangle]
pub static mut value4: ::core::ffi::c_int = 4 as ::core::ffi::c_int;
#[no_mangle]
pub static mut allocated_keys: ::core::ffi::c_int = 0 as ::core::ffi::c_int;
#[no_mangle]
pub static mut allocated_values: ::core::ffi::c_int = 0 as ::core::ffi::c_int;
#[no_mangle]
pub unsafe extern "C" fn generate_hash_table() -> *mut HashTable {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    let mut value: *mut ::core::ffi::c_char = ::core::ptr::null_mut::<::core::ffi::c_char>();
    let mut i: ::core::ffi::c_int = 0;
    hash_table = hash_table_new(
        Some(string_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            string_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        value = alloc_test_strdup(&raw mut buf as *mut ::core::ffi::c_char);
        hash_table_insert(hash_table, value as HashTableKey, value as HashTableValue);
        i += 1;
    }
    hash_table_register_free_functions(
        hash_table,
        None,
        Some(alloc_test_free as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ()),
    );
    return hash_table;
}
#[no_mangle]
pub unsafe extern "C" fn test_hash_table_new_free() {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    hash_table = hash_table_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label: {
        if !hash_table.is_null() {
        } else {
            __assert_fail(
                b"hash_table != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                82 as ::core::ffi::c_uint,
                b"void test_hash_table_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_insert(
        hash_table,
        &raw mut value1 as HashTableKey,
        &raw mut value1 as HashTableValue,
    );
    hash_table_insert(
        hash_table,
        &raw mut value2 as HashTableKey,
        &raw mut value2 as HashTableValue,
    );
    hash_table_insert(
        hash_table,
        &raw mut value3 as HashTableKey,
        &raw mut value3 as HashTableValue,
    );
    hash_table_insert(
        hash_table,
        &raw mut value4 as HashTableKey,
        &raw mut value4 as HashTableValue,
    );
    hash_table_free(hash_table);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    hash_table = hash_table_new(
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
        if hash_table.is_null() {
        } else {
            __assert_fail(
                b"hash_table == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                99 as ::core::ffi::c_uint,
                b"void test_hash_table_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if alloc_test_get_allocated() == 0 as size_t {
        } else {
            __assert_fail(
                b"alloc_test_get_allocated() == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                100 as ::core::ffi::c_uint,
                b"void test_hash_table_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(1 as ::core::ffi::c_int);
    hash_table = hash_table_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    '_c2rust_label_2: {
        if hash_table.is_null() {
        } else {
            __assert_fail(
                b"hash_table == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                104 as ::core::ffi::c_uint,
                b"void test_hash_table_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if alloc_test_get_allocated() == 0 as size_t {
        } else {
            __assert_fail(
                b"alloc_test_get_allocated() == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                105 as ::core::ffi::c_uint,
                b"void test_hash_table_new_free(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_hash_table_insert_lookup() {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    let mut value: *mut ::core::ffi::c_char = ::core::ptr::null_mut::<::core::ffi::c_char>();
    let mut i: ::core::ffi::c_int = 0;
    hash_table = generate_hash_table();
    '_c2rust_label: {
        if hash_table_num_entries(hash_table) == 10000 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"hash_table_num_entries(hash_table) == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                121 as ::core::ffi::c_uint,
                b"void test_hash_table_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        value = hash_table_lookup(
            hash_table,
            &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
        ) as *mut ::core::ffi::c_char;
        '_c2rust_label_0: {
            if strcmp(value, &raw mut buf as *mut ::core::ffi::c_char) == 0 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"strcmp(value, buf) == 0\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    129 as ::core::ffi::c_uint,
                    b"void test_hash_table_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    sprintf(
        &raw mut buf as *mut ::core::ffi::c_char,
        b"%i\0" as *const u8 as *const ::core::ffi::c_char,
        -(1 as ::core::ffi::c_int),
    );
    '_c2rust_label_1: {
        if hash_table_lookup(
            hash_table,
            &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"hash_table_lookup(hash_table, buf) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                135 as ::core::ffi::c_uint,
                b"void test_hash_table_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    sprintf(
        &raw mut buf as *mut ::core::ffi::c_char,
        b"%i\0" as *const u8 as *const ::core::ffi::c_char,
        NUM_TEST_VALUES,
    );
    '_c2rust_label_2: {
        if hash_table_lookup(
            hash_table,
            &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"hash_table_lookup(hash_table, buf) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                137 as ::core::ffi::c_uint,
                b"void test_hash_table_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    sprintf(
        &raw mut buf as *mut ::core::ffi::c_char,
        b"%i\0" as *const u8 as *const ::core::ffi::c_char,
        12345 as ::core::ffi::c_int,
    );
    hash_table_insert(
        hash_table,
        &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
        alloc_test_strdup(b"hello world\0" as *const u8 as *const ::core::ffi::c_char)
            as HashTableValue,
    );
    value = hash_table_lookup(
        hash_table,
        &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
    ) as *mut ::core::ffi::c_char;
    '_c2rust_label_3: {
        if strcmp(
            value,
            b"hello world\0" as *const u8 as *const ::core::ffi::c_char,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"strcmp(value, \"hello world\") == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                144 as ::core::ffi::c_uint,
                b"void test_hash_table_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_free(hash_table);
}
#[no_mangle]
pub unsafe extern "C" fn test_hash_table_remove() {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    hash_table = generate_hash_table();
    '_c2rust_label: {
        if hash_table_num_entries(hash_table) == 10000 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"hash_table_num_entries(hash_table) == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                156 as ::core::ffi::c_uint,
                b"void test_hash_table_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    sprintf(
        &raw mut buf as *mut ::core::ffi::c_char,
        b"%i\0" as *const u8 as *const ::core::ffi::c_char,
        5000 as ::core::ffi::c_int,
    );
    '_c2rust_label_0: {
        if !hash_table_lookup(
            hash_table,
            &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"hash_table_lookup(hash_table, buf) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                158 as ::core::ffi::c_uint,
                b"void test_hash_table_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_remove(
        hash_table,
        &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
    );
    '_c2rust_label_1: {
        if hash_table_num_entries(hash_table) == 9999 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"hash_table_num_entries(hash_table) == 9999\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                166 as ::core::ffi::c_uint,
                b"void test_hash_table_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if hash_table_lookup(
            hash_table,
            &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
        )
        .is_null()
        {
        } else {
            __assert_fail(
                b"hash_table_lookup(hash_table, buf) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                170 as ::core::ffi::c_uint,
                b"void test_hash_table_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    sprintf(
        &raw mut buf as *mut ::core::ffi::c_char,
        b"%i\0" as *const u8 as *const ::core::ffi::c_char,
        -(1 as ::core::ffi::c_int),
    );
    hash_table_remove(
        hash_table,
        &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
    );
    '_c2rust_label_3: {
        if hash_table_num_entries(hash_table) == 9999 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"hash_table_num_entries(hash_table) == 9999\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                177 as ::core::ffi::c_uint,
                b"void test_hash_table_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_free(hash_table);
}
#[no_mangle]
pub unsafe extern "C" fn test_hash_table_iterating() {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    let mut iterator: HashTableIterator = _HashTableIterator {
        hash_table: ::core::ptr::null_mut::<HashTable>(),
        next_entry: ::core::ptr::null_mut::<HashTableEntry>(),
        next_chain: 0,
    };
    let mut count: ::core::ffi::c_int = 0;
    hash_table = generate_hash_table();
    count = 0 as ::core::ffi::c_int;
    hash_table_iterate(hash_table, &raw mut iterator);
    while hash_table_iter_has_more(&raw mut iterator) != 0 {
        hash_table_iter_next(&raw mut iterator);
        count += 1;
    }
    '_c2rust_label: {
        if count == 10000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"count == NUM_TEST_VALUES\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                202 as ::core::ffi::c_uint,
                b"void test_hash_table_iterating(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    let mut pair: HashTablePair = hash_table_iter_next(&raw mut iterator);
    '_c2rust_label_0: {
        if pair.value.is_null() {
        } else {
            __assert_fail(
                b"pair.value == HASH_TABLE_NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                207 as ::core::ffi::c_uint,
                b"void test_hash_table_iterating(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_free(hash_table);
    hash_table = hash_table_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    hash_table_iterate(hash_table, &raw mut iterator);
    '_c2rust_label_1: {
        if hash_table_iter_has_more(&raw mut iterator) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"hash_table_iter_has_more(&iterator) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                217 as ::core::ffi::c_uint,
                b"void test_hash_table_iterating(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_free(hash_table);
}
#[no_mangle]
pub unsafe extern "C" fn test_hash_table_iterating_remove() {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    let mut iterator: HashTableIterator = _HashTableIterator {
        hash_table: ::core::ptr::null_mut::<HashTable>(),
        next_entry: ::core::ptr::null_mut::<HashTableEntry>(),
        next_chain: 0,
    };
    let mut buf: [::core::ffi::c_char; 10] = [0; 10];
    let mut val: *mut ::core::ffi::c_char = ::core::ptr::null_mut::<::core::ffi::c_char>();
    let mut pair: HashTablePair = _HashTablePair {
        key: ::core::ptr::null_mut::<::core::ffi::c_void>(),
        value: ::core::ptr::null_mut::<::core::ffi::c_void>(),
    };
    let mut count: ::core::ffi::c_int = 0;
    let mut removed: ::core::ffi::c_uint = 0;
    let mut i: ::core::ffi::c_int = 0;
    hash_table = generate_hash_table();
    count = 0 as ::core::ffi::c_int;
    removed = 0 as ::core::ffi::c_uint;
    hash_table_iterate(hash_table, &raw mut iterator);
    while hash_table_iter_has_more(&raw mut iterator) != 0 {
        pair = hash_table_iter_next(&raw mut iterator);
        val = pair.value as *mut ::core::ffi::c_char;
        if atoi(val) % 100 as ::core::ffi::c_int == 0 as ::core::ffi::c_int {
            hash_table_remove(hash_table, val as HashTableKey);
            removed = removed.wrapping_add(1);
        }
        count += 1;
    }
    '_c2rust_label: {
        if removed == 100 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"removed == 100\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                265 as ::core::ffi::c_uint,
                b"void test_hash_table_iterating_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if count == 10000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"count == NUM_TEST_VALUES\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                266 as ::core::ffi::c_uint,
                b"void test_hash_table_iterating_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if hash_table_num_entries(hash_table)
            == (10000 as ::core::ffi::c_uint).wrapping_sub(removed)
        {
        } else {
            __assert_fail(
                b"hash_table_num_entries(hash_table) == NUM_TEST_VALUES - removed\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                269 as ::core::ffi::c_uint,
                b"void test_hash_table_iterating_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        sprintf(
            &raw mut buf as *mut ::core::ffi::c_char,
            b"%i\0" as *const u8 as *const ::core::ffi::c_char,
            i,
        );
        if i % 100 as ::core::ffi::c_int == 0 as ::core::ffi::c_int {
            '_c2rust_label_2: {
                if hash_table_lookup(
                    hash_table,
                    &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
                )
                .is_null()
                {
                } else {
                    __assert_fail(
                        b"hash_table_lookup(hash_table, buf) == NULL\0" as *const u8
                            as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        277 as ::core::ffi::c_uint,
                        b"void test_hash_table_iterating_remove(void)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
        } else {
            '_c2rust_label_3: {
                if !hash_table_lookup(
                    hash_table,
                    &raw mut buf as *mut ::core::ffi::c_char as HashTableKey,
                )
                .is_null()
                {
                } else {
                    __assert_fail(
                        b"hash_table_lookup(hash_table, buf) != NULL\0" as *const u8
                            as *const ::core::ffi::c_char,
                        b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                            as *const u8 as *const ::core::ffi::c_char,
                        279 as ::core::ffi::c_uint,
                        b"void test_hash_table_iterating_remove(void)\0" as *const u8
                            as *const ::core::ffi::c_char,
                    );
                }
            };
        }
        i += 1;
    }
    hash_table_free(hash_table);
}
#[no_mangle]
pub unsafe extern "C" fn new_key(mut value: ::core::ffi::c_int) -> *mut ::core::ffi::c_int {
    let mut result: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    result = alloc_test_malloc(::core::mem::size_of::<::core::ffi::c_int>() as size_t)
        as *mut ::core::ffi::c_int;
    *result = value;
    allocated_keys += 1;
    return result;
}
#[no_mangle]
pub unsafe extern "C" fn free_key(mut key: *mut ::core::ffi::c_void) {
    alloc_test_free(key);
    allocated_keys -= 1;
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
pub unsafe extern "C" fn test_hash_table_free_functions() {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    let mut key: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    hash_table = hash_table_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    hash_table_register_free_functions(
        hash_table,
        Some(free_key as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ()),
        Some(free_value as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ()),
    );
    allocated_values = 0 as ::core::ffi::c_int;
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        key = new_key(i);
        value = new_value(99 as ::core::ffi::c_int);
        hash_table_insert(hash_table, key as HashTableKey, value as HashTableValue);
        i += 1;
    }
    '_c2rust_label: {
        if allocated_keys == 10000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_keys == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                356 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if allocated_values == 10000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_values == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                357 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = NUM_TEST_VALUES / 2 as ::core::ffi::c_int;
    hash_table_remove(hash_table, &raw mut i as HashTableKey);
    '_c2rust_label_1: {
        if allocated_keys == 10000 as ::core::ffi::c_int - 1 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_keys == NUM_TEST_VALUES - 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                364 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if allocated_values == 10000 as ::core::ffi::c_int - 1 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_values == NUM_TEST_VALUES - 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                365 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    key = new_key(NUM_TEST_VALUES / 3 as ::core::ffi::c_int);
    value = new_value(999 as ::core::ffi::c_int);
    '_c2rust_label_3: {
        if allocated_keys == 10000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_keys == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                372 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if allocated_values == 10000 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_values == NUM_TEST_VALUES\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                373 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_insert(hash_table, key as HashTableKey, value as HashTableValue);
    '_c2rust_label_5: {
        if allocated_keys == 10000 as ::core::ffi::c_int - 1 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_keys == NUM_TEST_VALUES - 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                377 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_6: {
        if allocated_values == 10000 as ::core::ffi::c_int - 1 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_values == NUM_TEST_VALUES - 1\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                378 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_free(hash_table);
    '_c2rust_label_7: {
        if allocated_keys == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_keys == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                384 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_8: {
        if allocated_values == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"allocated_values == 0\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                385 as ::core::ffi::c_uint,
                b"void test_hash_table_free_functions(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_hash_table_out_of_memory() {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    let mut values: [::core::ffi::c_int; 66] = [0; 66];
    let mut i: ::core::ffi::c_uint = 0;
    hash_table = hash_table_new(
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
        if hash_table_insert(
            hash_table,
            (&raw mut values as *mut ::core::ffi::c_int).offset(0 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as HashTableKey,
            (&raw mut values as *mut ::core::ffi::c_int).offset(0 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as HashTableValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"hash_table_insert(hash_table, &values[0], &values[0]) == 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                402 as ::core::ffi::c_uint,
                b"void test_hash_table_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if hash_table_num_entries(hash_table) == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"hash_table_num_entries(hash_table) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                403 as ::core::ffi::c_uint,
                b"void test_hash_table_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(-(1 as ::core::ffi::c_int));
    i = 0 as ::core::ffi::c_uint;
    while i < 65 as ::core::ffi::c_uint {
        values[i as usize] = i as ::core::ffi::c_int;
        '_c2rust_label_1: {
            if hash_table_insert(
                hash_table,
                (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as HashTableKey,
                (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                    as *mut ::core::ffi::c_int as HashTableValue,
            ) != 0 as ::core::ffi::c_int
            {
            } else {
                __assert_fail(
                    b"hash_table_insert(hash_table, &values[i], &values[i]) != 0\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    417 as ::core::ffi::c_uint,
                    b"void test_hash_table_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_2: {
            if hash_table_num_entries(hash_table) == i.wrapping_add(1 as ::core::ffi::c_uint) {
            } else {
                __assert_fail(
                    b"hash_table_num_entries(hash_table) == i + 1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    418 as ::core::ffi::c_uint,
                    b"void test_hash_table_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    '_c2rust_label_3: {
        if hash_table_num_entries(hash_table) == 65 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"hash_table_num_entries(hash_table) == 65\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                421 as ::core::ffi::c_uint,
                b"void test_hash_table_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    values[65 as ::core::ffi::c_int as usize] = 65 as ::core::ffi::c_int;
    '_c2rust_label_4: {
        if hash_table_insert(
            hash_table,
            (&raw mut values as *mut ::core::ffi::c_int).offset(65 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as HashTableKey,
            (&raw mut values as *mut ::core::ffi::c_int).offset(65 as ::core::ffi::c_int as isize)
                as *mut ::core::ffi::c_int as HashTableValue,
        ) == 0 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"hash_table_insert(hash_table, &values[65], &values[65]) == 0\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                429 as ::core::ffi::c_uint,
                b"void test_hash_table_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_5: {
        if hash_table_num_entries(hash_table) == 65 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"hash_table_num_entries(hash_table) == 65\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                430 as ::core::ffi::c_uint,
                b"void test_hash_table_out_of_memory(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    hash_table_free(hash_table);
}
#[no_mangle]
pub unsafe extern "C" fn test_hash_iterator_key_pair() {
    let mut hash_table: *mut HashTable = ::core::ptr::null_mut::<HashTable>();
    let mut iterator: HashTableIterator = _HashTableIterator {
        hash_table: ::core::ptr::null_mut::<HashTable>(),
        next_entry: ::core::ptr::null_mut::<HashTableEntry>(),
        next_chain: 0,
    };
    let mut pair: HashTablePair = _HashTablePair {
        key: ::core::ptr::null_mut::<::core::ffi::c_void>(),
        value: ::core::ptr::null_mut::<::core::ffi::c_void>(),
    };
    hash_table = hash_table_new(
        Some(int_hash as unsafe extern "C" fn(*mut ::core::ffi::c_void) -> ::core::ffi::c_uint),
        Some(
            int_equal
                as unsafe extern "C" fn(
                    *mut ::core::ffi::c_void,
                    *mut ::core::ffi::c_void,
                ) -> ::core::ffi::c_int,
        ),
    );
    hash_table_insert(
        hash_table,
        &raw mut value1 as HashTableKey,
        &raw mut value1 as HashTableValue,
    );
    hash_table_insert(
        hash_table,
        &raw mut value2 as HashTableKey,
        &raw mut value2 as HashTableValue,
    );
    hash_table_iterate(hash_table, &raw mut iterator);
    while hash_table_iter_has_more(&raw mut iterator) != 0 {
        pair = hash_table_iter_next(&raw mut iterator);
        let mut key: *mut ::core::ffi::c_int = pair.key as *mut ::core::ffi::c_int;
        let mut val: *mut ::core::ffi::c_int = pair.value as *mut ::core::ffi::c_int;
        '_c2rust_label: {
            if *key == *val {
            } else {
                __assert_fail(
                    b"*key == *val\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-hash-table.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    458 as ::core::ffi::c_uint,
                    b"void test_hash_iterator_key_pair()\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
    }
    hash_table_free(hash_table);
}
static mut tests: [UnitTestFunction; 9] = unsafe {
    [
        Some(test_hash_table_new_free as unsafe extern "C" fn() -> ()),
        Some(test_hash_table_insert_lookup as unsafe extern "C" fn() -> ()),
        Some(test_hash_table_remove as unsafe extern "C" fn() -> ()),
        Some(test_hash_table_iterating as unsafe extern "C" fn() -> ()),
        Some(test_hash_table_iterating_remove as unsafe extern "C" fn() -> ()),
        Some(test_hash_table_free_functions as unsafe extern "C" fn() -> ()),
        Some(test_hash_table_out_of_memory as unsafe extern "C" fn() -> ()),
        ::core::mem::transmute::<Option<unsafe extern "C" fn() -> ()>, UnitTestFunction>(Some(
            test_hash_iterator_key_pair,
        )),
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
