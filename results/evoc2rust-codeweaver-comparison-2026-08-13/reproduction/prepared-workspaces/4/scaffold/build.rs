fn main() {
    cc::Build::new()
        .include("fixed/support/src")
        .include("fixed/support/test")
        .define("ALLOC_TESTING", None)
        .file("fixed/support/src/compare-int.c")
        .compile("vivo_support");
}
