extern "C" {
    fn alloc_test_malloc(bytes: size_t) -> *mut ::core::ffi::c_void;
    fn alloc_test_free(ptr: *mut ::core::ffi::c_void);
}
pub type size_t = usize;
pub type __uint16_t = u16;
pub type __uint32_t = u32;
pub type __uint64_t = u64;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _AVLTree {
    pub root_node: *mut AVLTreeNode,
    pub compare_func: AVLTreeCompareFunc,
    pub num_nodes: ::core::ffi::c_uint,
}
pub type AVLTreeCompareFunc =
    Option<unsafe extern "C" fn(AVLTreeValue, AVLTreeValue) -> ::core::ffi::c_int>;
pub type AVLTreeValue = *mut ::core::ffi::c_void;
pub type AVLTreeNode = _AVLTreeNode;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _AVLTreeNode {
    pub children: [*mut AVLTreeNode; 2],
    pub parent: *mut AVLTreeNode,
    pub key: AVLTreeKey,
    pub value: AVLTreeValue,
    pub height: ::core::ffi::c_int,
}
pub type AVLTreeKey = *mut ::core::ffi::c_void;
pub type AVLTree = _AVLTree;
pub type AVLTreeNodeSide = ::core::ffi::c_uint;
pub const AVL_TREE_NODE_RIGHT: AVLTreeNodeSide = 1;
pub const AVL_TREE_NODE_LEFT: AVLTreeNodeSide = 0;
pub const NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
#[inline]
unsafe extern "C" fn __bswap_16(mut __bsx: __uint16_t) -> __uint16_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __bswap_32(mut __bsx: __uint32_t) -> __uint32_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __bswap_64(mut __bsx: __uint64_t) -> __uint64_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __uint16_identity(mut __x: __uint16_t) -> __uint16_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __uint32_identity(mut __x: __uint32_t) -> __uint32_t {
    unimplemented!("CodeWeaver must implement this function")
}
#[inline]
unsafe extern "C" fn __uint64_identity(mut __x: __uint64_t) -> __uint64_t {
    unimplemented!("CodeWeaver must implement this function")
}
pub const AVL_TREE_NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
#[no_mangle]
pub unsafe extern "C" fn avl_tree_new(mut compare_func: AVLTreeCompareFunc) -> *mut AVLTree {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_free_subtree(mut tree: *mut AVLTree, mut node: *mut AVLTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_free(mut tree: *mut AVLTree) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_subtree_height(mut node: *mut AVLTreeNode) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_update_height(mut node: *mut AVLTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_node_parent_side(mut node: *mut AVLTreeNode) -> AVLTreeNodeSide {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_node_replace(
    mut tree: *mut AVLTree,
    mut node1: *mut AVLTreeNode,
    mut node2: *mut AVLTreeNode,
) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_rotate(
    mut tree: *mut AVLTree,
    mut node: *mut AVLTreeNode,
    mut direction: AVLTreeNodeSide,
) -> *mut AVLTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_node_balance(
    mut tree: *mut AVLTree,
    mut node: *mut AVLTreeNode,
) -> *mut AVLTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_balance_to_root(mut tree: *mut AVLTree, mut node: *mut AVLTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_insert(
    mut tree: *mut AVLTree,
    mut key: AVLTreeKey,
    mut value: AVLTreeValue,
) -> *mut AVLTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_node_get_replacement(
    mut tree: *mut AVLTree,
    mut node: *mut AVLTreeNode,
) -> *mut AVLTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_remove_node(mut tree: *mut AVLTree, mut node: *mut AVLTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_remove(
    mut tree: *mut AVLTree,
    mut key: AVLTreeKey,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_lookup_node(
    mut tree: *mut AVLTree,
    mut key: AVLTreeKey,
) -> *mut AVLTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_lookup(
    mut tree: *mut AVLTree,
    mut key: AVLTreeKey,
) -> AVLTreeValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_root_node(mut tree: *mut AVLTree) -> *mut AVLTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_node_key(mut node: *mut AVLTreeNode) -> AVLTreeKey {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_node_value(mut node: *mut AVLTreeNode) -> AVLTreeValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_node_child(
    mut node: *mut AVLTreeNode,
    mut side: AVLTreeNodeSide,
) -> *mut AVLTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_node_parent(mut node: *mut AVLTreeNode) -> *mut AVLTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_num_entries(mut tree: *mut AVLTree) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn avl_tree_to_array_add_subtree(
    mut subtree: *mut AVLTreeNode,
    mut array: *mut AVLTreeValue,
    mut index: *mut ::core::ffi::c_int,
) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn avl_tree_to_array(mut tree: *mut AVLTree) -> *mut AVLTreeValue {
    unimplemented!("CodeWeaver must implement this function")
}
