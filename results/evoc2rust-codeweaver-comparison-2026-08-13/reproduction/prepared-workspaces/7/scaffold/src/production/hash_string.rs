extern "C" {
    fn tolower(__c: ::core::ffi::c_int) -> ::core::ffi::c_int;
}
#[no_mangle]
pub unsafe extern "C" fn string_hash(mut string: *mut ::core::ffi::c_void) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
#[no_mangle]
pub unsafe extern "C" fn string_nocase_hash(
    mut string: *mut ::core::ffi::c_void,
) -> ::core::ffi::c_uint {
    unimplemented!("CodeWeaver must implement this function")
}
