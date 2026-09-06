/* KentScript VM in C (fallback from assembly) */
#include <stdint.h>
#include <stdio.h>

#define STACK_SIZE 4096

static int64_t vm_stack[STACK_SIZE];
static int vm_sp = 0;
static int64_t vm_regs[16];

void ks_vm_init() {
    vm_sp = 0;
    for (int i = 0; i < 16; i++) {
        vm_regs[i] = 0;
    }
}

void ks_vm_push(int64_t value) {
    if (vm_sp < STACK_SIZE) {
        vm_stack[vm_sp++] = value;
    }
}

int64_t ks_vm_pop() {
    if (vm_sp > 0) {
        return vm_stack[--vm_sp];
    }
    return 0;
}

void ks_vm_add() {
    int64_t b = ks_vm_pop();
    int64_t a = ks_vm_pop();
    ks_vm_push(a + b);
}

void ks_vm_sub() {
    int64_t b = ks_vm_pop();
    int64_t a = ks_vm_pop();
    ks_vm_push(a - b);
}

void ks_vm_mul() {
    int64_t b = ks_vm_pop();
    int64_t a = ks_vm_pop();
    ks_vm_push(a * b);
}

void ks_vm_div() {
    int64_t b = ks_vm_pop();
    int64_t a = ks_vm_pop();
    if (b != 0) {
        ks_vm_push(a / b);
    } else {
        ks_vm_push(0);
    }
}

int ks_vm_get_sp() {
    return vm_sp;
}

int64_t ks_vm_peek() {
    if (vm_sp > 0) {
        return vm_stack[vm_sp - 1];
    }
    return 0;
}
