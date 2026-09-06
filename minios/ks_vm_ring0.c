/*
 * ============================================================================
 * KentScript Ring-0 VM (ks_vm_ring0.c)
 * ============================================================================
 * 
 * This is a bytecode interpreter for KentScript that executes at ring-0
 * with full hardware access.
 * 
 * Features:
 * - Stack-based VM (like Python bytecode, Lua VM, JVM bytecode)
 * - Supports basic types: int, float, string
 * - Can access hardware directly (no OS mediation)
 * - Can manipulate page tables, interrupt handlers, device I/O
 * - Ring-0 privileged operations available via syscalls/intrinsics
 * 
 * This would be compiled into the kernel and executed directly.
 */

#include <stdint.h>
#include <stddef.h>

/* ========================================================================== */
/* TYPES & CONSTANTS                                                         */
/* ========================================================================== */

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t i8;
typedef int16_t i16;
typedef int32_t i32;
typedef int64_t i64;
typedef double f64;

// KentScript value type (tagged union)
typedef struct {
    u64 tag;          // 0=int, 1=float, 2=string, 3=pointer
    union {
        i64 i;
        f64 f;
        u64 p;        // pointer
    } data;
} KSValue;

// VM opcodes
typedef enum {
    KS_NOP = 0,
    KS_CONST_INT,         // Load integer constant
    KS_CONST_FLOAT,       // Load float constant
    KS_CONST_STR,         // Load string constant
    KS_LOAD_VAR,          // Load variable
    KS_STORE_VAR,         // Store variable
    KS_PUSH,              // Push value to stack
    KS_POP,               // Pop value from stack
    KS_ADD,               // Add top two stack values
    KS_SUB,               // Subtract
    KS_MUL,               // Multiply
    KS_DIV,               // Divide
    KS_MOD,               // Modulo
    KS_AND,               // Bitwise AND
    KS_OR,                // Bitwise OR
    KS_XOR,               // Bitwise XOR
    KS_SHL,               // Shift left
    KS_SHR,               // Shift right
    KS_EQ,                // Equals
    KS_LT,                // Less than
    KS_GT,                // Greater than
    KS_JMP,               // Jump
    KS_JIF,               // Jump if false
    KS_CALL,              // Call function
    KS_RET,               // Return from function
    KS_PRINT,             // Print value to serial console
    KS_HALT,              // Halt CPU
    KS_READ_MSR,          // Read Model-Specific Register
    KS_WRITE_MSR,         // Write Model-Specific Register
    KS_IN,                // Port input
    KS_OUT,               // Port output
    KS_READ_MEM,          // Read memory address (any physical addr)
    KS_WRITE_MEM,         // Write memory address (any physical addr)
    KS_ALLOC,             // Allocate memory
    KS_FREE,              // Free memory
    KS_CLI,               // Clear interrupts
    KS_STI,               // Set interrupts
    KS_CPUID,             // CPUID instruction
    KS_MOV_CR,            // Move to/from control register
    KS_END = 255,
} KSOp;

// VM context
typedef struct {
    KSValue *stack;
    u32 stack_ptr;
    u32 stack_size;
    
    KSValue *vars;         // Local variables
    u32 var_count;
    
    u8 *code;              // Bytecode
    u32 code_ptr;
    u32 code_size;
    
    u64 *constants;        // Constant pool
    u32 const_count;
    
    u64 cpu_flags;         // Saved CPU flags
    int halted;
} KSVM;

/* ========================================================================== */
/* VM CREATION & DESTRUCTION                                                 */
/* ========================================================================== */

KSVM *ks_vm_create(u32 stack_size, u32 code_size) {
    // In real code, would use kmalloc from bare-metal runtime
    // For now, just allocate statically
    static KSVM vm_singleton;
    static KSValue stack_buffer[4096];
    static KSValue vars_buffer[256];
    static u8 code_buffer[65536];
    
    KSVM *vm = &vm_singleton;
    vm->stack = stack_buffer;
    vm->stack_size = 4096;
    vm->stack_ptr = 0;
    vm->vars = vars_buffer;
    vm->var_count = 256;
    vm->code = code_buffer;
    vm->code_size = 65536;
    vm->code_ptr = 0;
    vm->halted = 0;
    
    return vm;
}

/* ========================================================================== */
/* STACK OPERATIONS                                                          */
/* ========================================================================== */

static void ks_push(KSVM *vm, KSValue v) {
    if (vm->stack_ptr >= vm->stack_size) {
        // Stack overflow - halt
        vm->halted = 1;
        return;
    }
    vm->stack[vm->stack_ptr++] = v;
}

static KSValue ks_pop(KSVM *vm) {
    if (vm->stack_ptr == 0) {
        // Stack underflow
        vm->halted = 1;
        return (KSValue){0};
    }
    return vm->stack[--vm->stack_ptr];
}

static KSValue ks_peek(KSVM *vm) {
    if (vm->stack_ptr == 0) return (KSValue){0};
    return vm->stack[vm->stack_ptr - 1];
}

/* ========================================================================== */
/* BUILTIN FUNCTIONS (I/O, HARDWARE ACCESS)                                  */
/* ========================================================================== */

// Serial console output (via bare-metal runtime)
extern void printf_serial(const char *fmt, ...);

static void ks_builtin_print(KSValue v) {
    switch (v.tag) {
        case 0:  // int
            printf_serial("%d", v.data.i);
            break;
        case 1:  // float
            printf_serial("%f", v.data.f);
            break;
        case 2:  // string
            printf_serial((const char *)v.data.p);
            break;
        default:
            printf_serial("(unknown)");
    }
}

// Ring-0: Direct memory read
static KSValue ks_builtin_read_mem(u64 addr) {
    u64 value = *(u64 *)addr;  // Direct dereference at ring-0!
    return (KSValue){.tag = 0, .data.i = (i64)value};
}

// Ring-0: Direct memory write
static void ks_builtin_write_mem(u64 addr, u64 value) {
    *(u64 *)addr = value;  // Direct write at ring-0!
}

// Ring-0: Port I/O input
static KSValue ks_builtin_port_in(u16 port) {
    u32 value;
    asm volatile("inl %1, %0" : "=a"(value) : "d"(port));
    return (KSValue){.tag = 0, .data.i = value};
}

// Ring-0: Port I/O output
static void ks_builtin_port_out(u16 port, u32 value) {
    asm volatile("outl %0, %1" : : "a"(value), "d"(port));
}

// Ring-0: Read MSR (Model-Specific Register)
static KSValue ks_builtin_read_msr(u32 msr) {
    u32 eax, edx;
    asm volatile("rdmsr" : "=a"(eax), "=d"(edx) : "c"(msr));
    u64 value = ((u64)edx << 32) | eax;
    return (KSValue){.tag = 0, .data.i = (i64)value};
}

// Ring-0: Write MSR
static void ks_builtin_write_msr(u32 msr, u64 value) {
    asm volatile("wrmsr" : : "a"(value & 0xFFFFFFFF), "d"(value >> 32), "c"(msr));
}

// Ring-0: CPUID instruction
static KSValue ks_builtin_cpuid(u32 leaf) {
    u32 eax = leaf, ebx = 0, ecx = 0, edx = 0;
    asm volatile("cpuid" : "+a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx));
    return (KSValue){.tag = 0, .data.i = eax};
}

// Ring-0: CLI (Clear Interrupts)
static void ks_builtin_cli(void) {
    asm volatile("cli");
}

// Ring-0: STI (Set Interrupts)
static void ks_builtin_sti(void) {
    asm volatile("sti");
}

// Ring-0: HLT (Halt CPU)
static void ks_builtin_hlt(void) {
    asm volatile("hlt");
}

/* ========================================================================== */
/* VM EXECUTION ENGINE                                                       */
/* ========================================================================== */

void ks_vm_run(KSVM *vm) {
    printf_serial("\n[KentScript VM] Starting execution at ring-0\n");
    printf_serial("[KentScript VM] Full hardware access enabled\n\n");
    
    while (!vm->halted && vm->code_ptr < vm->code_size) {
        u8 op = vm->code[vm->code_ptr++];
        
        switch (op) {
            case KS_NOP:
                // No operation
                break;
            
            case KS_CONST_INT: {
                // Load integer constant from next 8 bytes
                i64 val = *(i64 *)&vm->code[vm->code_ptr];
                vm->code_ptr += 8;
                ks_push(vm, (KSValue){.tag = 0, .data.i = val});
                break;
            }
            
            case KS_PRINT: {
                // Print top stack value
                KSValue v = ks_pop(vm);
                ks_builtin_print(v);
                break;
            }
            
            case KS_ADD: {
                KSValue b = ks_pop(vm);
                KSValue a = ks_pop(vm);
                i64 result = a.data.i + b.data.i;
                ks_push(vm, (KSValue){.tag = 0, .data.i = result});
                break;
            }
            
            case KS_SUB: {
                KSValue b = ks_pop(vm);
                KSValue a = ks_pop(vm);
                i64 result = a.data.i - b.data.i;
                ks_push(vm, (KSValue){.tag = 0, .data.i = result});
                break;
            }
            
            case KS_MUL: {
                KSValue b = ks_pop(vm);
                KSValue a = ks_pop(vm);
                i64 result = a.data.i * b.data.i;
                ks_push(vm, (KSValue){.tag = 0, .data.i = result});
                break;
            }
            
            case KS_DIV: {
                KSValue b = ks_pop(vm);
                KSValue a = ks_pop(vm);
                if (b.data.i == 0) {
                    vm->halted = 1;
                    printf_serial("ERROR: Division by zero\n");
                } else {
                    i64 result = a.data.i / b.data.i;
                    ks_push(vm, (KSValue){.tag = 0, .data.i = result});
                }
                break;
            }
            
            // Ring-0 specific operations
            case KS_READ_MEM: {
                // Pop address, read 8 bytes at ring-0, push result
                KSValue addr = ks_pop(vm);
                KSValue result = ks_builtin_read_mem(addr.data.i);
                ks_push(vm, result);
                printf_serial("[VM] Read memory at 0x%x: 0x%x\n", addr.data.i, result.data.i);
                break;
            }
            
            case KS_WRITE_MEM: {
                // Pop value, pop address, write at ring-0
                KSValue val = ks_pop(vm);
                KSValue addr = ks_pop(vm);
                ks_builtin_write_mem(addr.data.i, val.data.i);
                printf_serial("[VM] Wrote memory at 0x%x: 0x%x\n", addr.data.i, val.data.i);
                break;
            }
            
            case KS_IN: {
                // Port input
                KSValue port = ks_pop(vm);
                KSValue result = ks_builtin_port_in(port.data.i);
                ks_push(vm, result);
                printf_serial("[VM] Port IN 0x%x: 0x%x\n", port.data.i, result.data.i);
                break;
            }
            
            case KS_OUT: {
                // Port output
                KSValue val = ks_pop(vm);
                KSValue port = ks_pop(vm);
                ks_builtin_port_out(port.data.i, val.data.i);
                printf_serial("[VM] Port OUT 0x%x: 0x%x\n", port.data.i, val.data.i);
                break;
            }
            
            case KS_READ_MSR: {
                // Read MSR
                KSValue msr = ks_pop(vm);
                KSValue result = ks_builtin_read_msr(msr.data.i);
                ks_push(vm, result);
                printf_serial("[VM] Read MSR 0x%x: 0x%x\n", msr.data.i, result.data.i);
                break;
            }
            
            case KS_WRITE_MSR: {
                // Write MSR
                KSValue val = ks_pop(vm);
                KSValue msr = ks_pop(vm);
                ks_builtin_write_msr(msr.data.i, val.data.i);
                printf_serial("[VM] Wrote MSR 0x%x: 0x%x\n", msr.data.i, val.data.i);
                break;
            }
            
            case KS_CPUID: {
                // CPUID instruction
                KSValue leaf = ks_pop(vm);
                KSValue result = ks_builtin_cpuid(leaf.data.i);
                ks_push(vm, result);
                printf_serial("[VM] CPUID leaf 0x%x: 0x%x\n", leaf.data.i, result.data.i);
                break;
            }
            
            case KS_CLI:
                ks_builtin_cli();
                printf_serial("[VM] Interrupts disabled (CLI)\n");
                break;
            
            case KS_STI:
                ks_builtin_sti();
                printf_serial("[VM] Interrupts enabled (STI)\n");
                break;
            
            case KS_HALT:
                vm->halted = 1;
                printf_serial("[VM] Halt instruction executed\n");
                break;
            
            default:
                printf_serial("ERROR: Unknown opcode 0x%x at PC=0x%x\n", op, vm->code_ptr - 1);
                vm->halted = 1;
        }
    }
    
    printf_serial("\n[KentScript VM] Execution complete\n");
}

/* ========================================================================== */
/* TESTING: Sample KentScript bytecode                                       */
/* ========================================================================== */

// Example bytecode program:
// push 5
// push 3
// add
// print
// halt

static u8 sample_program[] = {
    KS_CONST_INT,
    5, 0, 0, 0, 0, 0, 0, 0,  // 5 in little-endian
    KS_CONST_INT,
    3, 0, 0, 0, 0, 0, 0, 0,  // 3
    KS_ADD,
    KS_PRINT,
    KS_HALT,
};

void ks_vm_run_test(void) {
    printf_serial("\n=== KentScript Ring-0 VM Test ===\n\n");
    
    KSVM *vm = ks_vm_create(4096, 65536);
    
    // Load sample program
    for (int i = 0; i < sizeof(sample_program); i++) {
        vm->code[i] = sample_program[i];
    }
    vm->code_size = sizeof(sample_program);
    
    printf_serial("[VM] Sample program: 5 + 3 = ?\n");
    printf_serial("[VM] Result: ");
    
    ks_vm_run(vm);
    
    printf_serial("\n\n");
}
