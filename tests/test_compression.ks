:: Test Phase 10 - Compression

print("Test: GZIP");
let gzip_enc = system_compress_gzip("test data");
let gzip_dec = system_decompress_gzip(gzip_enc);
if gzip_dec == "test data" {
    print("✓ gzip works");
}

print("\nTest: ZLIB");
let zlib_enc = system_compress_zlib("test data");
let zlib_dec = system_decompress_zlib(zlib_enc);
if zlib_dec == "test data" {
    print("✓ zlib works");
}

print("\nTest: BZ2");
let bz2_enc = system_compress_bz2("test data");
let bz2_dec = system_decompress_bz2(bz2_enc);
if bz2_dec == "test data" {
    print("✓ bz2 works");
}

print("\nTest: LZMA");
let lzma_enc = system_compress_lzma("test data");
let lzma_dec = system_decompress_lzma(lzma_enc);
if lzma_dec == "test data" {
    print("✓ lzma works");
}

print("\n=== Phase 10 Compression Complete ===");
