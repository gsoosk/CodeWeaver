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
pub struct _RBTree {
    pub root_node: *mut RBTreeNode,
    pub compare_func: RBTreeCompareFunc,
    pub num_nodes: ::core::ffi::c_int,
}
pub type RBTreeCompareFunc =
    Option<unsafe extern "C" fn(RBTreeValue, RBTreeValue) -> ::core::ffi::c_int>;
pub type RBTreeValue = *mut ::core::ffi::c_void;
pub type RBTreeNode = _RBTreeNode;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct _RBTreeNode {
    pub color: RBTreeNodeColor,
    pub key: RBTreeKey,
    pub value: RBTreeValue,
    pub parent: *mut RBTreeNode,
    pub children: [*mut RBTreeNode; 2],
}
pub type RBTreeKey = *mut ::core::ffi::c_void;
pub type RBTreeNodeColor = ::core::ffi::c_uint;
pub const RB_TREE_NODE_BLACK: RBTreeNodeColor = 1;
pub const RB_TREE_NODE_RED: RBTreeNodeColor = 0;
pub type RBTree = _RBTree;
pub type RBTreeNodeSide = ::core::ffi::c_uint;
pub const RB_TREE_NODE_RIGHT: RBTreeNodeSide = 1;
pub const RB_TREE_NODE_LEFT: RBTreeNodeSide = 0;
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
pub const RB_TREE_NULL: *mut ::core::ffi::c_void = ::core::ptr::null_mut::<::core::ffi::c_void>();
unsafe extern "C" fn rb_tree_node_side(mut node: *mut RBTreeNode) -> RBTreeNodeSide {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_node_sibling(mut node: *mut RBTreeNode) -> *mut RBTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_node_uncle(mut node: *mut RBTreeNode) -> *mut RBTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_node_replace(
    mut tree: *mut RBTree,
    mut node1: *mut RBTreeNode,
    mut node2: *mut RBTreeNode,
) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_rotate(
    mut tree: *mut RBTree,
    mut node: *mut RBTreeNode,
    mut direction: RBTreeNodeSide,
) -> *mut RBTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_new(mut compare_func: RBTreeCompareFunc) -> *mut RBTree {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_free_subtree(mut node: *mut RBTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_free(mut tree: *mut RBTree) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_insert_case1(mut tree: *mut RBTree, mut node: *mut RBTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_insert_case2(mut tree: *mut RBTree, mut node: *mut RBTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_insert_case3(mut tree: *mut RBTree, mut node: *mut RBTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_insert_case4(mut tree: *mut RBTree, mut node: *mut RBTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
unsafe extern "C" fn rb_tree_insert_case5(mut tree: *mut RBTree, mut node: *mut RBTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_insert(
    mut tree: *mut RBTree,
    mut key: RBTreeKey,
    mut value: RBTreeValue,
) -> *mut RBTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_lookup_node(
    mut tree: *mut RBTree,
    mut key: RBTreeKey,
) -> *mut RBTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_lookup(mut tree: *mut RBTree, mut key: RBTreeKey) -> RBTreeValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_remove_node(mut tree: *mut RBTree, mut node: *mut RBTreeNode) {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_remove(
    mut tree: *mut RBTree,
    mut key: RBTreeKey,
) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_root_node(mut tree: *mut RBTree) -> *mut RBTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_node_key(mut node: *mut RBTreeNode) -> RBTreeKey {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_node_value(mut node: *mut RBTreeNode) -> RBTreeValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_node_child(
    mut node: *mut RBTreeNode,
    mut side: RBTreeNodeSide,
) -> *mut RBTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_node_parent(mut node: *mut RBTreeNode) -> *mut RBTreeNode {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_to_array(mut tree: *mut RBTree) -> *mut RBTreeValue {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn rb_tree_num_entries(mut tree: *mut RBTree) -> ::core::ffi::c_int {
    unimplemented!("CodeWeaver must implement this function")
}
