extern "C" {
    pub type _AVLTree;
    pub type _AVLTreeNode;
    fn __assert_fail(
        __assertion: *const ::core::ffi::c_char,
        __file: *const ::core::ffi::c_char,
        __line: ::core::ffi::c_uint,
        __function: *const ::core::ffi::c_char,
    ) -> !;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
    fn alloc_test_set_limit(alloc_count: ::core::ffi::c_int);
    fn run_tests(tests_0: *mut UnitTestFunction);
    fn avl_tree_new(compare_func: AVLTreeCompareFunc) -> *mut AVLTree;
    fn avl_tree_free(tree: *mut AVLTree);
    fn avl_tree_insert(
        tree: *mut AVLTree,
        key: AVLTreeKey,
        value: AVLTreeValue,
    ) -> *mut AVLTreeNode;
    fn avl_tree_remove(tree: *mut AVLTree, key: AVLTreeKey) -> ::core::ffi::c_int;
    fn avl_tree_lookup_node(tree: *mut AVLTree, key: AVLTreeKey) -> *mut AVLTreeNode;
    fn avl_tree_lookup(tree: *mut AVLTree, key: AVLTreeKey) -> AVLTreeValue;
    fn avl_tree_root_node(tree: *mut AVLTree) -> *mut AVLTreeNode;
    fn avl_tree_node_key(node: *mut AVLTreeNode) -> AVLTreeKey;
    fn avl_tree_node_value(node: *mut AVLTreeNode) -> AVLTreeValue;
    fn avl_tree_node_child(node: *mut AVLTreeNode, side: AVLTreeNodeSide) -> *mut AVLTreeNode;
    fn avl_tree_node_parent(node: *mut AVLTreeNode) -> *mut AVLTreeNode;
    fn avl_tree_subtree_height(node: *mut AVLTreeNode) -> ::core::ffi::c_int;
    fn avl_tree_to_array(tree: *mut AVLTree) -> *mut AVLTreeValue;
    fn avl_tree_num_entries(tree: *mut AVLTree) -> ::core::ffi::c_uint;
    fn int_compare(
        location1: *mut ::core::ffi::c_void,
        location2: *mut ::core::ffi::c_void,
    ) -> ::core::ffi::c_int;
}
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
pub type UnitTestFunction = Option<unsafe extern "C" fn() -> ()>;
pub type AVLTree = _AVLTree;
pub type AVLTreeKey = *mut ::core::ffi::c_void;
pub type AVLTreeValue = *mut ::core::ffi::c_void;
pub type AVLTreeNode = _AVLTreeNode;
pub type AVLTreeNodeSide = ::core::ffi::c_uint;
pub const AVL_TREE_NODE_RIGHT: AVLTreeNodeSide = 1;
pub const AVL_TREE_NODE_LEFT: AVLTreeNodeSide = 0;
pub type AVLTreeCompareFunc =
    Option<unsafe extern "C" fn(AVLTreeValue, AVLTreeValue) -> ::core::ffi::c_int>;
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
pub unsafe extern "C" fn find_subtree_height(mut node: *mut AVLTreeNode) -> ::core::ffi::c_int {
    let mut left_subtree: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut right_subtree: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut left_height: ::core::ffi::c_int = 0;
    let mut right_height: ::core::ffi::c_int = 0;
    if node.is_null() {
        return 0 as ::core::ffi::c_int;
    }
    left_subtree = avl_tree_node_child(node, AVL_TREE_NODE_LEFT);
    right_subtree = avl_tree_node_child(node, AVL_TREE_NODE_RIGHT);
    left_height = find_subtree_height(left_subtree);
    right_height = find_subtree_height(right_subtree);
    if left_height > right_height {
        return left_height + 1 as ::core::ffi::c_int;
    } else {
        return right_height + 1 as ::core::ffi::c_int;
    };
}
#[no_mangle]
pub static mut counter: ::core::ffi::c_int = 0;
#[no_mangle]
pub unsafe extern "C" fn validate_subtree(mut node: *mut AVLTreeNode) -> ::core::ffi::c_int {
    let mut left_node: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut right_node: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut left_height: ::core::ffi::c_int = 0;
    let mut right_height: ::core::ffi::c_int = 0;
    let mut key: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    if node.is_null() {
        return 0 as ::core::ffi::c_int;
    }
    left_node = avl_tree_node_child(node, AVL_TREE_NODE_LEFT);
    right_node = avl_tree_node_child(node, AVL_TREE_NODE_RIGHT);
    if !left_node.is_null() {
        '_c2rust_label: {
            if avl_tree_node_parent(left_node) == node {
            } else {
                __assert_fail(
                    b"avl_tree_node_parent(left_node) == node\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    102 as ::core::ffi::c_uint,
                    b"int validate_subtree(AVLTreeNode *)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
    }
    if !right_node.is_null() {
        '_c2rust_label_0: {
            if avl_tree_node_parent(right_node) == node {
            } else {
                __assert_fail(
                    b"avl_tree_node_parent(right_node) == node\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    105 as ::core::ffi::c_uint,
                    b"int validate_subtree(AVLTreeNode *)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
    }
    left_height = validate_subtree(left_node);
    key = avl_tree_node_key(node) as *mut ::core::ffi::c_int;
    '_c2rust_label_1: {
        if *key > counter {
        } else {
            __assert_fail(
                b"*key > counter\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                117 as ::core::ffi::c_uint,
                b"int validate_subtree(AVLTreeNode *)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    counter = *key;
    right_height = validate_subtree(right_node);
    '_c2rust_label_2: {
        if avl_tree_subtree_height(left_node) == left_height {
        } else {
            __assert_fail(
                b"avl_tree_subtree_height(left_node) == left_height\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                125 as ::core::ffi::c_uint,
                b"int validate_subtree(AVLTreeNode *)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if avl_tree_subtree_height(right_node) == right_height {
        } else {
            __assert_fail(
                b"avl_tree_subtree_height(right_node) == right_height\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                126 as ::core::ffi::c_uint,
                b"int validate_subtree(AVLTreeNode *)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_4: {
        if left_height - right_height < 2 as ::core::ffi::c_int
            && right_height - left_height < 2 as ::core::ffi::c_int
        {
        } else {
            __assert_fail(
                b"left_height - right_height < 2 && right_height - left_height < 2\0"
                    as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                131 as ::core::ffi::c_uint,
                b"int validate_subtree(AVLTreeNode *)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    if left_height > right_height {
        return left_height + 1 as ::core::ffi::c_int;
    } else {
        return right_height + 1 as ::core::ffi::c_int;
    };
}
#[no_mangle]
pub unsafe extern "C" fn validate_tree(mut tree: *mut AVLTree) {
    let mut root_node: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut height: ::core::ffi::c_int = 0;
    root_node = avl_tree_root_node(tree);
    if !root_node.is_null() {
        height = find_subtree_height(root_node);
        '_c2rust_label: {
            if avl_tree_subtree_height(root_node) == height {
            } else {
                __assert_fail(
                    b"avl_tree_subtree_height(root_node) == height\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    151 as ::core::ffi::c_uint,
                    b"void validate_tree(AVLTree *)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
    }
    counter = -(1 as ::core::ffi::c_int);
    validate_subtree(root_node);
}
#[no_mangle]
pub unsafe extern "C" fn create_tree() -> *mut AVLTree {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
    let mut i: ::core::ffi::c_int = 0;
    tree = avl_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        AVLTreeCompareFunc,
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
        avl_tree_insert(
            tree,
            (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as AVLTreeKey,
            (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as AVLTreeValue,
        );
        i += 1;
    }
    return tree;
}
#[no_mangle]
pub unsafe extern "C" fn test_avl_tree_new() {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
    tree = avl_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        AVLTreeCompareFunc,
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
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                181 as ::core::ffi::c_uint,
                b"void test_avl_tree_new(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_0: {
        if avl_tree_root_node(tree).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_root_node(tree) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                182 as ::core::ffi::c_uint,
                b"void test_avl_tree_new(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_1: {
        if avl_tree_num_entries(tree) == 0 as ::core::ffi::c_uint {
        } else {
            __assert_fail(
                b"avl_tree_num_entries(tree) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                183 as ::core::ffi::c_uint,
                b"void test_avl_tree_new(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    avl_tree_free(tree);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    tree = avl_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        AVLTreeCompareFunc,
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
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                193 as ::core::ffi::c_uint,
                b"void test_avl_tree_new(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn test_avl_tree_insert_lookup() {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
    let mut node: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut i: ::core::ffi::c_uint = 0;
    let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    tree = avl_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        AVLTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    i = 0 as ::core::ffi::c_uint;
    while i < NUM_TEST_VALUES as ::core::ffi::c_uint {
        test_array[i as usize] = i as ::core::ffi::c_int;
        avl_tree_insert(
            tree,
            (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as AVLTreeKey,
            (&raw mut test_array as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as AVLTreeValue,
        );
        '_c2rust_label: {
            if avl_tree_num_entries(tree) == i.wrapping_add(1 as ::core::ffi::c_uint) {
            } else {
                __assert_fail(
                    b"avl_tree_num_entries(tree) == i + 1\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    213 as ::core::ffi::c_uint,
                    b"void test_avl_tree_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        validate_tree(tree);
        i = i.wrapping_add(1);
    }
    '_c2rust_label_0: {
        if !avl_tree_root_node(tree).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_root_node(tree) != NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                217 as ::core::ffi::c_uint,
                b"void test_avl_tree_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 0 as ::core::ffi::c_uint;
    while i < NUM_TEST_VALUES as ::core::ffi::c_uint {
        node = avl_tree_lookup_node(tree, &raw mut i as AVLTreeKey);
        '_c2rust_label_1: {
            if !node.is_null() {
            } else {
                __assert_fail(
                    b"node != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    223 as ::core::ffi::c_uint,
                    b"void test_avl_tree_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        value = avl_tree_node_key(node) as *mut ::core::ffi::c_int;
        '_c2rust_label_2: {
            if *value == i as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"*value == (int) i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    225 as ::core::ffi::c_uint,
                    b"void test_avl_tree_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        value = avl_tree_node_value(node) as *mut ::core::ffi::c_int;
        '_c2rust_label_3: {
            if *value == i as ::core::ffi::c_int {
            } else {
                __assert_fail(
                    b"*value == (int) i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    227 as ::core::ffi::c_uint,
                    b"void test_avl_tree_insert_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    i = (NUM_TEST_VALUES + 100 as ::core::ffi::c_int) as ::core::ffi::c_uint;
    '_c2rust_label_4: {
        if avl_tree_lookup_node(tree, &raw mut i as AVLTreeKey).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_lookup_node(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                233 as ::core::ffi::c_uint,
                b"void test_avl_tree_insert_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    avl_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_avl_tree_child() {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
    let mut root: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut left: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut right: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut values: [::core::ffi::c_int; 3] = [
        1 as ::core::ffi::c_int,
        2 as ::core::ffi::c_int,
        3 as ::core::ffi::c_int,
    ];
    let mut p: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    let mut i: ::core::ffi::c_int = 0;
    tree = avl_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        AVLTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    i = 0 as ::core::ffi::c_int;
    while i < 3 as ::core::ffi::c_int {
        avl_tree_insert(
            tree,
            (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as AVLTreeKey,
            (&raw mut values as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as AVLTreeValue,
        );
        i += 1;
    }
    root = avl_tree_root_node(tree);
    p = avl_tree_node_value(root) as *mut ::core::ffi::c_int;
    '_c2rust_label: {
        if *p == 2 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"*p == 2\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                261 as ::core::ffi::c_uint,
                b"void test_avl_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    left = avl_tree_node_child(root, AVL_TREE_NODE_LEFT);
    p = avl_tree_node_value(left) as *mut ::core::ffi::c_int;
    '_c2rust_label_0: {
        if *p == 1 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"*p == 1\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                265 as ::core::ffi::c_uint,
                b"void test_avl_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    right = avl_tree_node_child(root, AVL_TREE_NODE_RIGHT);
    p = avl_tree_node_value(right) as *mut ::core::ffi::c_int;
    '_c2rust_label_1: {
        if *p == 3 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"*p == 3\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                269 as ::core::ffi::c_uint,
                b"void test_avl_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_2: {
        if avl_tree_node_child(root, 10000 as AVLTreeNodeSide).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_node_child(root, 10000) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                273 as ::core::ffi::c_uint,
                b"void test_avl_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    '_c2rust_label_3: {
        if avl_tree_node_child(root, 2 as AVLTreeNodeSide).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_node_child(root, 2) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                274 as ::core::ffi::c_uint,
                b"void test_avl_tree_child(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    avl_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_out_of_memory() {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
    let mut node: *mut AVLTreeNode = ::core::ptr::null_mut::<AVLTreeNode>();
    let mut i: ::core::ffi::c_int = 0;
    tree = create_tree();
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    i = 10000 as ::core::ffi::c_int;
    while i < 20000 as ::core::ffi::c_int {
        node = avl_tree_insert(tree, &raw mut i as AVLTreeKey, &raw mut i as AVLTreeValue);
        '_c2rust_label: {
            if node.is_null() {
            } else {
                __assert_fail(
                    b"node == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    297 as ::core::ffi::c_uint,
                    b"void test_out_of_memory(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        validate_tree(tree);
        i += 1;
    }
    avl_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_avl_tree_free() {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
    tree = avl_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        AVLTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    avl_tree_free(tree);
    tree = create_tree();
    avl_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_avl_tree_lookup() {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
    let mut i: ::core::ffi::c_int = 0;
    let mut value: *mut ::core::ffi::c_int = ::core::ptr::null_mut::<::core::ffi::c_int>();
    tree = create_tree();
    i = 0 as ::core::ffi::c_int;
    while i < NUM_TEST_VALUES {
        value = avl_tree_lookup(tree, &raw mut i as AVLTreeKey) as *mut ::core::ffi::c_int;
        '_c2rust_label: {
            if !value.is_null() {
            } else {
                __assert_fail(
                    b"value != NULL\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    332 as ::core::ffi::c_uint,
                    b"void test_avl_tree_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        '_c2rust_label_0: {
            if *value == i {
            } else {
                __assert_fail(
                    b"*value == i\0" as *const u8 as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    333 as ::core::ffi::c_uint,
                    b"void test_avl_tree_lookup(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i += 1;
    }
    i = -(1 as ::core::ffi::c_int);
    '_c2rust_label_1: {
        if avl_tree_lookup(tree, &raw mut i as AVLTreeKey).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_lookup(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                339 as ::core::ffi::c_uint,
                b"void test_avl_tree_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = NUM_TEST_VALUES + 1 as ::core::ffi::c_int;
    '_c2rust_label_2: {
        if avl_tree_lookup(tree, &raw mut i as AVLTreeKey).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_lookup(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                341 as ::core::ffi::c_uint,
                b"void test_avl_tree_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = 8724897 as ::core::ffi::c_int;
    '_c2rust_label_3: {
        if avl_tree_lookup(tree, &raw mut i as AVLTreeKey).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_lookup(tree, &i) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                343 as ::core::ffi::c_uint,
                b"void test_avl_tree_lookup(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    avl_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_avl_tree_remove() {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
    let mut i: ::core::ffi::c_int = 0;
    let mut x: ::core::ffi::c_int = 0;
    let mut y: ::core::ffi::c_int = 0;
    let mut z: ::core::ffi::c_int = 0;
    let mut value: ::core::ffi::c_int = 0;
    let mut expected_entries: ::core::ffi::c_uint = 0;
    tree = create_tree();
    i = NUM_TEST_VALUES + 100 as ::core::ffi::c_int;
    '_c2rust_label: {
        if avl_tree_remove(tree, &raw mut i as AVLTreeKey) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"avl_tree_remove(tree, &i) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                361 as ::core::ffi::c_uint,
                b"void test_avl_tree_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    i = -(1 as ::core::ffi::c_int);
    '_c2rust_label_0: {
        if avl_tree_remove(tree, &raw mut i as AVLTreeKey) == 0 as ::core::ffi::c_int {
        } else {
            __assert_fail(
                b"avl_tree_remove(tree, &i) == 0\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                363 as ::core::ffi::c_uint,
                b"void test_avl_tree_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    expected_entries = NUM_TEST_VALUES as ::core::ffi::c_uint;
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
                    if avl_tree_remove(tree, &raw mut value as AVLTreeKey)
                        != 0 as ::core::ffi::c_int
                    {
                    } else {
                        __assert_fail(
                            b"avl_tree_remove(tree, &value) != 0\0" as *const u8
                                as *const ::core::ffi::c_char,
                            b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                                as *const u8 as *const ::core::ffi::c_char,
                            376 as ::core::ffi::c_uint,
                            b"void test_avl_tree_remove(void)\0" as *const u8
                                as *const ::core::ffi::c_char,
                        );
                    }
                };
                validate_tree(tree);
                expected_entries = expected_entries.wrapping_sub(1 as ::core::ffi::c_uint);
                '_c2rust_label_2: {
                    if avl_tree_num_entries(tree) == expected_entries {
                    } else {
                        __assert_fail(
                            b"avl_tree_num_entries(tree) == expected_entries\0"
                                as *const u8 as *const ::core::ffi::c_char,
                            b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                                as *const u8 as *const ::core::ffi::c_char,
                            380 as ::core::ffi::c_uint,
                            b"void test_avl_tree_remove(void)\0" as *const u8
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
        if avl_tree_root_node(tree).is_null() {
        } else {
            __assert_fail(
                b"avl_tree_root_node(tree) == NULL\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                387 as ::core::ffi::c_uint,
                b"void test_avl_tree_remove(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    avl_tree_free(tree);
}
#[no_mangle]
pub unsafe extern "C" fn test_avl_tree_to_array() {
    let mut tree: *mut AVLTree = ::core::ptr::null_mut::<AVLTree>();
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
    let mut num_entries: ::core::ffi::c_uint = (::core::mem::size_of::<[::core::ffi::c_int; 10]>()
        as usize)
        .wrapping_div(::core::mem::size_of::<::core::ffi::c_int>() as usize)
        as ::core::ffi::c_uint;
    let mut i: ::core::ffi::c_uint = 0;
    let mut array: *mut *mut ::core::ffi::c_int =
        ::core::ptr::null_mut::<*mut ::core::ffi::c_int>();
    tree = avl_tree_new(::core::mem::transmute::<
        Option<
            unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
        >,
        AVLTreeCompareFunc,
    >(Some(
        int_compare
            as unsafe extern "C" fn(
                *mut ::core::ffi::c_void,
                *mut ::core::ffi::c_void,
            ) -> ::core::ffi::c_int,
    )));
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        avl_tree_insert(
            tree,
            (&raw mut entries as *mut ::core::ffi::c_int).offset(i as isize)
                as *mut ::core::ffi::c_int as AVLTreeKey,
            NULL,
        );
        i = i.wrapping_add(1);
    }
    '_c2rust_label: {
        if avl_tree_num_entries(tree) == num_entries {
        } else {
            __assert_fail(
                b"avl_tree_num_entries(tree) == num_entries\0" as *const u8
                    as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                409 as ::core::ffi::c_uint,
                b"void test_avl_tree_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    array = avl_tree_to_array(tree) as *mut *mut ::core::ffi::c_int;
    i = 0 as ::core::ffi::c_uint;
    while i < num_entries {
        '_c2rust_label_0: {
            if **array.offset(i as isize) == sorted[i as usize] {
            } else {
                __assert_fail(
                    b"*array[i] == sorted[i]\0" as *const u8
                        as *const ::core::ffi::c_char,
                    b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                        as *const u8 as *const ::core::ffi::c_char,
                    416 as ::core::ffi::c_uint,
                    b"void test_avl_tree_to_array(void)\0" as *const u8
                        as *const ::core::ffi::c_char,
                );
            }
        };
        i = i.wrapping_add(1);
    }
    alloc_test_free(array as *mut ::core::ffi::c_void);
    alloc_test_set_limit(0 as ::core::ffi::c_int);
    array = avl_tree_to_array(tree) as *mut *mut ::core::ffi::c_int;
    '_c2rust_label_1: {
        if array.is_null() {
        } else {
            __assert_fail(
                b"array == NULL\0" as *const u8 as *const ::core::ffi::c_char,
                b"/opt/codeweaver-evoc2rust/artifact/01-BlueOS2_Translation/Input/01-Primary/test/test-avl-tree.c\0"
                    as *const u8 as *const ::core::ffi::c_char,
                426 as ::core::ffi::c_uint,
                b"void test_avl_tree_to_array(void)\0" as *const u8
                    as *const ::core::ffi::c_char,
            );
        }
    };
    validate_tree(tree);
    avl_tree_free(tree);
}
static mut tests: [UnitTestFunction; 9] = unsafe {
    [
        Some(test_avl_tree_new as unsafe extern "C" fn() -> ()),
        Some(test_avl_tree_free as unsafe extern "C" fn() -> ()),
        Some(test_avl_tree_child as unsafe extern "C" fn() -> ()),
        Some(test_avl_tree_insert_lookup as unsafe extern "C" fn() -> ()),
        Some(test_avl_tree_lookup as unsafe extern "C" fn() -> ()),
        Some(test_avl_tree_remove as unsafe extern "C" fn() -> ()),
        Some(test_avl_tree_to_array as unsafe extern "C" fn() -> ()),
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
