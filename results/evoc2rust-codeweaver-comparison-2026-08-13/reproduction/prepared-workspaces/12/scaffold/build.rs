fn main() {
    cc::Build::new()
        .include("fixed/support/src")
        .include("fixed/support/test")
        .define("ALLOC_TESTING", None)
        .file("fixed/support/src/compare-int.c")
        .file("fixed/support/src/compare-pointer.c")
        .file("fixed/support/src/compare-string.c")
        .file("fixed/support/src/hash-int.c")
        .file("fixed/support/src/hash-pointer.c")
        .file("fixed/support/src/hash-string.c")
        .compile("vivo_support");
}
