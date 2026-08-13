extern "C" {
    pub type _RBTree;
    pub type _RBTreeNode;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn rb_tree_new(compare_func: RBTreeCompareFunc) -> *mut RBTree;
    fn rb_tree_free(tree: *mut RBTree);
    fn rb_tree_insert(tree: *mut RBTree, key: RBTreeKey, value: RBTreeValue) -> *mut RBTreeNode;
    fn rb_tree_remove(tree: *mut RBTree, key: RBTreeKey) -> ::core::ffi::c_int;
    fn rb_tree_lookup_node(tree: *mut RBTree, key: RBTreeKey) -> *mut RBTreeNode;
    fn rb_tree_lookup(tree: *mut RBTree, key: RBTreeKey) -> RBTreeValue;
    fn rb_tree_root_node(tree: *mut RBTree) -> *mut RBTreeNode;
    fn rb_tree_node_key(node: *mut RBTreeNode) -> RBTreeKey;
    fn rb_tree_node_value(node: *mut RBTreeNode) -> RBTreeValue;
    fn rb_tree_node_child(node: *mut RBTreeNode, side: RBTreeNodeSide) -> *mut RBTreeNode;
    fn rb_tree_to_array(tree: *mut RBTree) -> *mut RBTreeValue;
    fn rb_tree_num_entries(tree: *mut RBTree) -> ::core::ffi::c_int;
    fn int_compare(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
}
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type RBTree = _RBTree;
pub type RBTreeKey = *mut ::core::ffi::c_void;
pub type RBTreeValue = *mut ::core::ffi::c_void;
pub type RBTreeNode = _RBTreeNode;
pub type RBTreeCompareFunc =
    Option<unsafe extern "C" fn(RBTreeValue, RBTreeValue) -> ::core::ffi::c_int>;
pub type RBTreeNodeSide = ::core::ffi::c_uint;
pub const RB_TREE_NODE_RIGHT: RBTreeNodeSide = 1;
pub const RB_TREE_NODE_LEFT: RBTreeNodeSide = 0;
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
pub const NUM_TEST_VALUES: ::core::ffi::c_int = 1000 as ::core::ffi::c_int;
#[no_mangle]
pub static mut test_array: [::core::ffi::c_int; 1000] = [0; 1000];
#[no_mangle]
pub unsafe extern "C" fn find_subtree_height(mut node: *mut RBTreeNode) -> ::core::ffi::c_int {
    let mut left_subtree: *mut RBTreeNode = ::core::ptr::null_mut::<RBTreeNode>();
    let mut right_subtree: *mut RBTreeNode = ::core::ptr::null_mut::<RBTreeNode>();
    let mut left_height: ::core::ffi::c_int = 0;
    let mut right_height: ::core::ffi::c_int = 0;
    if node.is_null() {
        return 0 as ::core::ffi::c_int;
    }
    left_subtree = rb_tree_node_child(node, RB_TREE_NODE_LEFT);
    right_subtree = rb_tree_node_child(node, RB_TREE_NODE_RIGHT);
    left_height = find_subtree_height(left_subtree);
    right_height = find_subtree_height(right_subtree);
    if left_height > right_height {
        return left_height + 1 as ::core::ffi::c_int;
    } else {
        return right_height + 1 as ::core::ffi::c_int;
    };
}
#[no_mangle]
pub unsafe extern "C" fn validate_tree(mut tree: *mut RBTree) {}
#[no_mangle]
pub unsafe extern "C" fn create_tree() -> *mut RBTree {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    let mut i: ::core::ffi::c_int = 0;
    tree = rb_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        RBTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        test_array[i as usize] = i;
        rb_tree_insert(
            tree,
            (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as RBTreeKey,
            (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as RBTreeValue,
        );
        i += 1;
    }
    return tree;
}
#[no_mangle]
pub unsafe extern "C" fn test_rb_tree_new() {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    tree = rb_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        RBTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    '_c2rust_label: {
        if !tree.is_null() {
        } else {
            __assert_fail(
                b"tree != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                109 as ::core::ffi::c_uint,
                b"void test_rb_tree_new(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if rb_tree_root_node(tree).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_root_node(tree) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                110 as ::core::ffi::c_uint,
                b"void test_rb_tree_new(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if rb_tree_num_entries(tree) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"rb_tree_num_entries(tree) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                111 as ::core::ffi::c_uint,
                b"void test_rb_tree_new(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rb_tree_free(tree);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    tree = rb_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        RBTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    '_c2rust_label_2: {
        if tree.is_null() {
        } else {
            __assert_fail(
                b"tree == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                121 as ::core::ffi::c_uint,
                b"void test_rb_tree_new(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_rb_tree_insert_lookup() {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    let mut node: *mut RBTreeNode = ::core::ptr::null_mut::<RBTreeNode>();
    let mut i: ::core::ffi::c_int = 0;
    let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    tree = rb_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        RBTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        test_array[i as usize] = i;
        rb_tree_insert(
            tree,
            (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as RBTreeKey,
            (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as RBTreeValue,
        );
        '_c2rust_label: {
            if rb_tree_num_entries(tree) == i + 1 as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"rb_tree_num_entries(tree) == i + 1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    141 as ::core::ffi::c_uint,
                    b"void test_rb_tree_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        validate_tree(tree);
        i += 1;
    }
    '_c2rust_label_0: {
        if !rb_tree_root_node(tree).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_root_node(tree) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                145 as ::core::ffi::c_uint,
                b"void test_rb_tree_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        node = rb_tree_lookup_node(tree, &raw mut i as RBTreeKey);
        '_c2rust_label_1: {
            if !node.is_null() {
            } else {
                __assert_fail(
                    b"node != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    151 as ::core::ffi::c_uint,
                    b"void test_rb_tree_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        value = rb_tree_node_key(node) as *mut ::core::ffi::c_int;
        '_c2rust_label_2: {
            if *value == i {
            } else {
                __assert_fail(
                    b"*value == i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    153 as ::core::ffi::c_uint,
                    b"void test_rb_tree_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        value = rb_tree_node_value(node) as *mut ::core::ffi::c_int;
        '_c2rust_label_3: {
            if *value == i {
            } else {
                __assert_fail(
                    b"*value == i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    155 as ::core::ffi::c_uint,
                    b"void test_rb_tree_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    i = -(1 as ::core::ffi::c_int);
    '_c2rust_label_4: {
        if rb_tree_lookup_node(tree, &raw mut i as RBTreeKey).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_lookup_node(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                161 as ::core::ffi::c_uint,
                b"void test_rb_tree_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = NUM_TEST_VALUES + 100 as ::core::ffi::c_int;
    '_c2rust_label_5: {
        if rb_tree_lookup_node(tree, &raw mut i as RBTreeKey).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_lookup_node(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                163 as ::core::ffi::c_uint,
                b"void test_rb_tree_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rb_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_rb_tree_child() {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    let mut root: *mut RBTreeNode = ::core::ptr::null_mut::<RBTreeNode>();
    let mut left: *mut RBTreeNode = ::core::ptr::null_mut::<RBTreeNode>();
    let mut right: *mut RBTreeNode = ::core::ptr::null_mut::<RBTreeNode>();
    let mut values: [::core::ffi::c_int; 3] = [
        1 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        3 as ::core::ffi::c_int,
    ];
    let mut p: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    tree = rb_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        RBTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    i = 0 as ::core::ffi::c_int;
    while i < 3 as ::core::ffi::c_int {
        rb_tree_insert(
            tree,
            (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as RBTreeKey,
            (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as RBTreeValue,
        );
        i += 1;
    }
    root = rb_tree_root_node(tree);
    p = rb_tree_node_value(root) as *mut ::core::ffi::c_int;
    '_c2rust_label: {
        if *p == 2 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"*p == 2\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                191 as ::core::ffi::c_uint,
                b"void test_rb_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    left = rb_tree_node_child(root, RB_TREE_NODE_LEFT);
    p = rb_tree_node_value(left) as *mut ::core::ffi::c_int;
    '_c2rust_label_0: {
        if *p == 1 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"*p == 1\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                195 as ::core::ffi::c_uint,
                b"void test_rb_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    right = rb_tree_node_child(root, RB_TREE_NODE_RIGHT);
    p = rb_tree_node_value(right) as *mut ::core::ffi::c_int;
    '_c2rust_label_1: {
        if *p == 3 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"*p == 3\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                199 as ::core::ffi::c_uint,
                b"void test_rb_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if rb_tree_node_child(root, 10000 as RBTreeNodeSide).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_node_child(root, 10000) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                203 as ::core::ffi::c_uint,
                b"void test_rb_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if rb_tree_node_child(root, 2 as RBTreeNodeSide).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_node_child(root, 2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                204 as ::core::ffi::c_uint,
                b"void test_rb_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rb_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_out_of_memory() {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    let mut node: *mut RBTreeNode = ::core::ptr::null_mut::<RBTreeNode>();
    let mut i: ::core::ffi::c_int = 0;
    tree = create_tree();
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    i = 10000 as ::core::ffi::c_int;
    while i < 20000 as ::core::ffi::c_int {
        node = rb_tree_insert(tree, &raw mut i as RBTreeKey, &raw mut i as RBTreeValue);
        '_c2rust_label: {
            if node.is_null() {
            } else {
                __assert_fail(
                    b"node == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    227 as ::core::ffi::c_uint,
                    b"void test_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        validate_tree(tree);
        i += 1;
    }
    rb_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_rb_tree_free() {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    tree = rb_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        RBTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    rb_tree_free(tree);
    tree = create_tree();
    rb_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_rb_tree_lookup() {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    let mut i: ::core::ffi::c_int = 0;
    let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    tree = create_tree();
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        value = rb_tree_lookup(tree, &raw mut i as RBTreeKey) as *mut ::core::ffi::c_int;
        '_c2rust_label: {
            if !value.is_null() {
            } else {
                __assert_fail(
                    b"value != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    262 as ::core::ffi::c_uint,
                    b"void test_rb_tree_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_0: {
            if *value == i {
            } else {
                __assert_fail(
                    b"*value == i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    263 as ::core::ffi::c_uint,
                    b"void test_rb_tree_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    i = -(1 as ::core::ffi::c_int);
    '_c2rust_label_1: {
        if rb_tree_lookup(tree, &raw mut i as RBTreeKey).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_lookup(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                269 as ::core::ffi::c_uint,
                b"void test_rb_tree_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = NUM_TEST_VALUES + 1 as ::core::ffi::c_int;
    '_c2rust_label_2: {
        if rb_tree_lookup(tree, &raw mut i as RBTreeKey).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_lookup(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                271 as ::core::ffi::c_uint,
                b"void test_rb_tree_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 8724897 as ::core::ffi::c_int;
    '_c2rust_label_3: {
        if rb_tree_lookup(tree, &raw mut i as RBTreeKey).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_lookup(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                273 as ::core::ffi::c_uint,
                b"void test_rb_tree_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rb_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_rb_tree_remove() {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    let mut i: ::core::ffi::c_int = 0;
    let mut x: ::core::ffi::c_int = 0;
    let mut y: ::core::ffi::c_int = 0;
    let mut z: ::core::ffi::c_int = 0;
    let mut value: ::core::ffi::c_int = 0;
    let mut expected_entries: ::core::ffi::c_int = 0;
    tree = create_tree();
    i = NUM_TEST_VALUES + 100 as ::core::ffi::c_int;
    '_c2rust_label: {
        if rb_tree_remove(tree, &raw mut i as RBTreeKey) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"rb_tree_remove(tree, &i) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                291 as ::core::ffi::c_uint,
                b"void test_rb_tree_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = -(1 as ::core::ffi::c_int);
    '_c2rust_label_0: {
        if rb_tree_remove(tree, &raw mut i as RBTreeKey) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"rb_tree_remove(tree, &i) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                293 as ::core::ffi::c_uint,
                b"void test_rb_tree_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    expected_entries = NUM_TEST_VALUES;
    x = 0 as ::core::ffi::c_int;
    while x < 10 as ::core::ffi::c_int {
        y = 0 as ::core::ffi::c_int;
        while y < 10 as ::core::ffi::c_int {
            z = 0 as ::core::ffi::c_int;
            while z < 10 as ::core::ffi::c_int {
                value = z * 100 as ::core::ffi::c_int
                    + (9 as ::core::ffi::c_int - y) * 10 as ::core::ffi::c_int
                    + x;
                '_c2rust_label_1: {
                    if rb_tree_remove(tree, &raw mut value as RBTreeKey) != 0 as ::core::ffi::c_int
                    {
                    } else {
                        __assert_fail(
                            b"rb_tree_remove(tree, &value) != 0\0" as *const u8
                                as *const ::core::ffi::c_char,
                            b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                                as *const u8 as *const ::core::ffi::c_char,
                            306 as ::core::ffi::c_uint,
                            b"void test_rb_tree_remove(void)\0" as *const u8
                                as *const ::core::ffi::c_char,
                        );
                    }
                };
                validate_tree(tree);
                expected_entries -= 1 as ::core::ffi::c_int;
                '_c2rust_label_2: {
                    if rb_tree_num_entries(tree) == expected_entries {
                    } else {
                        __assert_fail(
                            b"rb_tree_num_entries(tree) == expected_entries\0"
                                as *const u8 as *const ::core::ffi::c_char,
                            b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                                as *const u8 as *const ::core::ffi::c_char,
                            310 as ::core::ffi::c_uint,
                            b"void test_rb_tree_remove(void)\0" as *const u8
                                as *const ::core::ffi::c_char,
                        );
                    }
                };
                z += 1;
            }
            y += 1;
        }
        x += 1;
    }
    '_c2rust_label_3: {
        if rb_tree_root_node(tree).is_null() {
        } else {
            __assert_fail(
                b"rb_tree_root_node(tree) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                317 as ::core::ffi::c_uint,
                b"void test_rb_tree_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    rb_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_rb_tree_to_array() {
    let mut tree: *mut RBTree = ::core::ptr::null_mut::<RBTree>();
    let mut entries: [::core::ffi::c_int; 10] = [
        89 as ::core::ffi::c_int,
        23 as ::core::ffi::c_int,
        42 as ::core::ffi::c_int,
        4 as ::core::ffi::c_int,
        16 as ::core::ffi::c_int,
        15 as ::core::ffi::c_int,
        8 as ::core::ffi::c_int,
        99 as ::core::ffi::c_int,
        50 as ::core::ffi::c_int,
        30 as ::core::ffi::c_int,
    ];
    let mut sorted: [::core::ffi::c_int; 10] = [
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
    let mut num_entries: ::core::ffi::c_int = (::core::mem::size_of::<[::core::ffi::c_int; 10]>()
        as usize)
        .wrapping_div(::core::mem::size_of::<::core::ffi::c_int>() as usize)
        as ::core::ffi::c_int;
    let mut i: ::core::ffi::c_int = 0;
    let mut array: *mut *mut ::core::ffi::c_int =
        ::core::ptr::null_mut::<*mut ::core::ffi::c_int>();
    tree = rb_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        RBTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    i = 0 as ::core::ffi::c_int;
    while i < num_entries {
        rb_tree_insert(
            tree,
            (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as RBTreeKey,
            NULL,
        );
        i += 1;
    }
    '_c2rust_label: {
        if rb_tree_num_entries(tree) == num_entries {
        } else {
            __assert_fail(
                b"rb_tree_num_entries(tree) == num_entries\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                339 as ::core::ffi::c_uint,
                b"void test_rb_tree_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    array = rb_tree_to_array(tree) as *mut *mut ::core::ffi::c_int;
    i = 0 as ::core::ffi::c_int;
    while i < num_entries {
        '_c2rust_label_0: {
            if **array.offset(i as isize) == sorted[i as usize] {
            } else {
                __assert_fail(
                    b"*array[i] == sorted[i]\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    346 as ::core::ffi::c_uint,
                    b"void test_rb_tree_to_array(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    alloc_test_free(array as *mut ::core::ffi::c_void);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    array = rb_tree_to_array(tree) as *mut *mut ::core::ffi::c_int;
    '_c2rust_label_1: {
        if array.is_null() {
        } else {
            __assert_fail(
                b"array == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-rb-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                356 as ::core::ffi::c_uint,
                b"void test_rb_tree_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    validate_tree(tree);
    rb_tree_free(tree);
}
static mut tests: [UnitTestFunction; 7] = unsafe {
    [
        Some(test_rb_tree_new as unsafe extern "C" fn() -> ()),
        Some(test_rb_tree_free as unsafe extern "C" fn() -> ()),
        Some(test_rb_tree_child as unsafe extern "C" fn() -> ()),
        Some(test_rb_tree_insert_lookup as unsafe extern "C" fn() -> ()),
        Some(test_rb_tree_lookup as unsafe extern "C" fn() -> ()),
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
