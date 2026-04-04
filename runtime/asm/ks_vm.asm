; KentScript Core VM in x86-64 Assembly
; Minimal bytecode interpreter

section .data
    stack_size equ 4096
    
section .bss
    vm_stack: resq stack_size    ; VM stack
    vm_sp: resq 1                 ; Stack pointer
    vm_ip: resq 1                 ; Instruction pointer
    vm_regs: resq 16              ; 16 general purpose registers

section .text
    global ks_vm_init
    global ks_vm_execute
    global ks_vm_push
    global ks_vm_pop
    global ks_vm_add
    global ks_vm_sub
    global ks_vm_mul
    global ks_vm_div

; Initialize VM
ks_vm_init:
    push rbp
    mov rbp, rsp
    
    ; Initialize stack pointer
    lea rax, [rel vm_stack]
    mov [rel vm_sp], rax
    
    ; Clear registers
    xor rcx, rcx
    lea rdi, [rel vm_regs]
.clear_loop:
    mov qword [rdi + rcx * 8], 0
    inc rcx
    cmp rcx, 16
    jl .clear_loop
    
    pop rbp
    ret

; Push value onto VM stack
; rdi = value to push
ks_vm_push:
    push rbp
    mov rbp, rsp
    
    mov rax, [rel vm_sp]
    mov [rax], rdi
    add rax, 8
    mov [rel vm_sp], rax
    
    pop rbp
    ret

; Pop value from VM stack
; Returns value in rax
ks_vm_pop:
    push rbp
    mov rbp, rsp
    
    mov rax, [rel vm_sp]
    sub rax, 8
    mov [rel vm_sp], rax
    mov rax, [rax]
    
    pop rbp
    ret

; Add top two stack values
ks_vm_add:
    push rbp
    mov rbp, rsp
    
    call ks_vm_pop
    mov rbx, rax
    call ks_vm_pop
    add rax, rbx
    mov rdi, rax
    call ks_vm_push
    
    pop rbp
    ret

; Subtract top two stack values
ks_vm_sub:
    push rbp
    mov rbp, rsp
    
    call ks_vm_pop
    mov rbx, rax
    call ks_vm_pop
    sub rax, rbx
    mov rdi, rax
    call ks_vm_push
    
    pop rbp
    ret

; Multiply top two stack values
ks_vm_mul:
    push rbp
    mov rbp, rsp
    
    call ks_vm_pop
    mov rbx, rax
    call ks_vm_pop
    imul rax, rbx
    mov rdi, rax
    call ks_vm_push
    
    pop rbp
    ret

; Divide top two stack values
ks_vm_div:
    push rbp
    mov rbp, rsp
    
    call ks_vm_pop
    mov rbx, rax
    call ks_vm_pop
    xor rdx, rdx
    idiv rbx
    mov rdi, rax
    call ks_vm_push
    
    pop rbp
    ret

; Execute bytecode
; rdi = bytecode pointer
; rsi = bytecode length
ks_vm_execute:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    
    mov r12, rdi              ; bytecode pointer
    mov r13, rsi              ; bytecode length
    xor rbx, rbx              ; instruction counter
    
.execute_loop:
    cmp rbx, r13
    jge .done
    
    movzx rax, byte [r12 + rbx]
    inc rbx
    
    ; Opcode dispatch
    cmp rax, 0x01             ; PUSH
    je .op_push
    cmp rax, 0x02             ; POP
    je .op_pop
    cmp rax, 0x10             ; ADD
    je .op_add
    cmp rax, 0x11             ; SUB
    je .op_sub
    cmp rax, 0x12             ; MUL
    je .op_mul
    cmp rax, 0x13             ; DIV
    je .op_div
    cmp rax, 0xFF             ; HALT
    je .done
    
    jmp .execute_loop

.op_push:
    mov rdi, qword [r12 + rbx]
    add rbx, 8
    call ks_vm_push
    jmp .execute_loop

.op_pop:
    call ks_vm_pop
    jmp .execute_loop

.op_add:
    call ks_vm_add
    jmp .execute_loop

.op_sub:
    call ks_vm_sub
    jmp .execute_loop

.op_mul:
    call ks_vm_mul
    jmp .execute_loop

.op_div:
    call ks_vm_div
    jmp .execute_loop

.done:
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
