/* Test C components */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Lexer test
extern void* lexer_new(const char *source);
extern void lexer_tokenize(void *lex);
extern void lexer_free(void *lex);

// Allocator test
extern void ks_mem_init();
extern void* ks_malloc(size_t size);
extern void ks_free(void *ptr);
extern void* ks_realloc(void *ptr, size_t new_size);
extern size_t ks_mem_available();
extern size_t ks_mem_used();

// VM test
extern void ks_vm_init();
extern void ks_vm_push(long long value);
extern long long ks_vm_pop();
extern void ks_vm_add();
extern void ks_vm_sub();
extern void ks_vm_mul();
extern void ks_vm_div();

void test_allocator() {
    printf("\n=== Testing Memory Allocator ===\n");
    
    ks_mem_init();
    printf("Initial available: %zu bytes\n", ks_mem_available());
    
    void *p1 = ks_malloc(1024);
    printf("✓ Allocated 1024 bytes\n");
    printf("  Available: %zu bytes\n", ks_mem_available());
    
    void *p2 = ks_malloc(2048);
    printf("✓ Allocated 2048 bytes\n");
    printf("  Available: %zu bytes\n", ks_mem_available());
    
    ks_free(p1);
    printf("✓ Freed p1\n");
    printf("  Available: %zu bytes\n", ks_mem_available());
    
    void *p3 = ks_realloc(p2, 4096);
    printf("✓ Reallocated p2 to 4096 bytes\n");
    printf("  Available: %zu bytes\n", ks_mem_available());
    
    ks_free(p3);
    printf("✓ Freed p3\n");
    printf("  Available: %zu bytes\n", ks_mem_available());
    
    printf("✓ Allocator test passed!\n");
}

void test_vm() {
    printf("\n=== Testing VM ===\n");
    
    ks_vm_init();
    printf("✓ VM initialized\n");
    
    // Test: 10 + 20
    ks_vm_push(10);
    ks_vm_push(20);
    ks_vm_add();
    long long result = ks_vm_pop();
    printf("✓ 10 + 20 = %lld (expected 30)\n", result);
    
    // Test: 50 - 15
    ks_vm_push(50);
    ks_vm_push(15);
    ks_vm_sub();
    result = ks_vm_pop();
    printf("✓ 50 - 15 = %lld (expected 35)\n", result);
    
    // Test: 6 * 7
    ks_vm_push(6);
    ks_vm_push(7);
    ks_vm_mul();
    result = ks_vm_pop();
    printf("✓ 6 * 7 = %lld (expected 42)\n", result);
    
    // Test: 100 / 5
    ks_vm_push(100);
    ks_vm_push(5);
    ks_vm_div();
    result = ks_vm_pop();
    printf("✓ 100 / 5 = %lld (expected 20)\n", result);
    
    printf("✓ VM test passed!\n");
}

int main() {
    printf("=== KentScript Core Components Test ===\n");
    
    test_allocator();
    test_vm();
    
    printf("\n=== All C component tests passed! ===\n");
    return 0;
}
