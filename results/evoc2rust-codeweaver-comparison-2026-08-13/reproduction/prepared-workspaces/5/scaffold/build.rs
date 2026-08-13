fn main() {
    cc::Build::new()
        .include("fixed/support/src")
        .include("fixed/support/test")
        .define("ALLOC_TESTING", None)
        .file("fixed/support/src/hash-string.c")
        .compile("vivo_support");
}
