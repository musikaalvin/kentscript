/* KentScript Memory Allocator in C */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define HEAP_SIZE (1024 * 1024 * 16)  // 16MB heap
#define BLOCK_MAGIC 0x4B53424C  // "KSBL"

typedef struct Block {
    uint32_t magic;
    size_t size;
    int is_free;
    struct Block *next;
} Block;

static uint8_t heap[HEAP_SIZE];
static Block *free_list = NULL;
static int initialized = 0;

void ks_mem_init() {
    if (initialized) return;
    
    free_list = (Block*)heap;
    free_list->magic = BLOCK_MAGIC;
    free_list->size = HEAP_SIZE - sizeof(Block);
    free_list->is_free = 1;
    free_list->next = NULL;
    
    initialized = 1;
}

void* ks_malloc(size_t size) {
    if (!initialized) ks_mem_init();
    if (size == 0) return NULL;
    
    // Align to 8 bytes
    size = (size + 7) & ~7;
    
    Block *current = free_list;
    Block *prev = NULL;
    
    while (current) {
        if (current->is_free && current->size >= size) {
            // Split block if large enough
            if (current->size >= size + sizeof(Block) + 64) {
                Block *new_block = (Block*)((uint8_t*)current + sizeof(Block) + size);
                new_block->magic = BLOCK_MAGIC;
                new_block->size = current->size - size - sizeof(Block);
                new_block->is_free = 1;
                new_block->next = current->next;
                
                current->size = size;
                current->next = new_block;
            }
            
            current->is_free = 0;
            return (void*)((uint8_t*)current + sizeof(Block));
        }
        
        prev = current;
        current = current->next;
    }
    
    return NULL;  // Out of memory
}

void ks_free(void *ptr) {
    if (!ptr) return;
    
    Block *block = (Block*)((uint8_t*)ptr - sizeof(Block));
    
    if (block->magic != BLOCK_MAGIC) {
        return;  // Invalid pointer
    }
    
    block->is_free = 1;
    
    // Coalesce with next block if free
    if (block->next && block->next->is_free) {
        block->size += sizeof(Block) + block->next->size;
        block->next = block->next->next;
    }
}

void* ks_realloc(void *ptr, size_t new_size) {
    if (!ptr) return ks_malloc(new_size);
    if (new_size == 0) {
        ks_free(ptr);
        return NULL;
    }
    
    Block *block = (Block*)((uint8_t*)ptr - sizeof(Block));
    if (block->magic != BLOCK_MAGIC) return NULL;
    
    if (block->size >= new_size) {
        return ptr;  // Already large enough
    }
    
    void *new_ptr = ks_malloc(new_size);
    if (new_ptr) {
        memcpy(new_ptr, ptr, block->size);
        ks_free(ptr);
    }
    
    return new_ptr;
}

void* ks_calloc(size_t count, size_t size) {
    size_t total = count * size;
    void *ptr = ks_malloc(total);
    if (ptr) {
        memset(ptr, 0, total);
    }
    return ptr;
}

size_t ks_mem_available() {
    if (!initialized) ks_mem_init();
    
    size_t available = 0;
    Block *current = free_list;
    
    while (current) {
        if (current->is_free) {
            available += current->size;
        }
        current = current->next;
    }
    
    return available;
}

size_t ks_mem_used() {
    return HEAP_SIZE - ks_mem_available();
}

#ifdef TEST_ALLOCATOR
#include <stdio.h>

int main() {
    printf("KentScript Memory Allocator Test\n");
    printf("Heap size: %d bytes\n", HEAP_SIZE);
    
    ks_mem_init();
    printf("Available: %zu bytes\n", ks_mem_available());
    
    void *p1 = ks_malloc(1024);
    printf("Allocated 1024 bytes, available: %zu\n", ks_mem_available());
    
    void *p2 = ks_malloc(2048);
    printf("Allocated 2048 bytes, available: %zu\n", ks_mem_available());
    
    ks_free(p1);
    printf("Freed p1, available: %zu\n", ks_mem_available());
    
    void *p3 = ks_malloc(512);
    printf("Allocated 512 bytes, available: %zu\n", ks_mem_available());
    
    ks_free(p2);
    ks_free(p3);
    printf("Freed all, available: %zu\n", ks_mem_available());
    
    return 0;
}
#endif
