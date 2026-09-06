; ============================================================================
; KentScript Bare-Metal Bootstrap - x86-64 BIOS Entry Point
; ============================================================================
; This is the first code to run on bare hardware (ring-0, EL0)
; No operating system. No libc. No dependencies.
; 
; Execution flow:
; 1. BIOS/bootloader jumps to this code at 0x7C00 or via Multiboot2
; 2. We set up minimal CPU state (GDT, stack, paging)
; 3. Jump to C runtime
; 4. C runtime initializes KentScript VM/interpreter
; 5. Execute KentScript bytecode or compiled code at ring-0

bits 16
org 0x7c00

; ============================================================================
; MULTIBOOT2 HEADER (for GRUB bootloaders)
; ============================================================================

ALIGN 8
mboot_header_start:
    dd 0xe85250d6              ; Multiboot2 magic number
    dd 0                       ; i386 protected mode
    dd mboot_header_end - mboot_header_start  ; Header length
    dd 0x100000000 - (0xe85250d6 + 0 + (mboot_header_end - mboot_header_start))

    ; Framebuffer tag (optional, for video output)
    ALIGN 8
    dw 5                       ; Tag type: framebuffer
    dw 1                       ; Flags: required
    dd 20                      ; Size
    dd 1024                    ; Width
    dd 768                     ; Height
    dd 32                      ; Bits per pixel

    ; End tag
    ALIGN 8
    dw 0                       ; Tag type: end
    dw 0                       ; Flags
    dd 8                       ; Size
mboot_header_end:

; ============================================================================
; 32-BIT PROTECTED MODE ENTRY (after bootloader setup)
; ============================================================================

ALIGN 16
start_32bit:
    ; At this point:
    ; - EBX = pointer to Multiboot2 info structure
    ; - We're in protected mode (32-bit)
    ; - Paging is NOT yet enabled
    ; - We're still in lower memory (0x7C00 or 0x100000)

    ; Disable interrupts
    cli

    ; Set up stack (grows downward)
    mov esp, stack_top

    ; Load GDT
    lgdt [gdt_ptr]

    ; Far jump to set CS to kernel code segment
    jmp 0x08:start_kernel

; ============================================================================
; GLOBAL DESCRIPTOR TABLE (GDT) - CPU memory segmentation
; ============================================================================

ALIGN 16
gdt:
    ; Null descriptor
    dq 0

    ; Code segment: base=0, limit=0xFFFFFFFF, ring-0, executable
    ; Flags: Present=1, DPL=0, Type=Code
    dq 0x00af9a000000ffff

    ; Data segment: base=0, limit=0xFFFFFFFF, ring-0, writable
    ; Flags: Present=1, DPL=0, Type=Data
    dq 0x00af92000000ffff

    ; Code segment for ring-3 (usermode)
    dq 0x00affa000000ffff

    ; Data segment for ring-3
    dq 0x00aff2000000ffff

gdt_ptr:
    dw gdt_ptr - gdt - 1       ; GDT size - 1
    dd gdt                     ; GDT address

; ============================================================================
; 64-BIT LONG MODE ENTRY
; ============================================================================

ALIGN 16
bits 32
start_kernel:
    ; We're now in 32-bit protected mode with kernel code segment

    ; Set up data segments
    mov ax, 0x10               ; Data segment selector
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; Check for long mode support (CPUID)
    mov eax, 0x80000001
    cpuid
    test edx, 1 << 29          ; LM flag
    jz no_long_mode

    ; Set up page tables for long mode
    ; Build minimal 4-level page table hierarchy
    ; PML4[0] -> PDP[0] -> PD[0] -> PT[0] -> physical page
    
    ; Clear page tables
    mov edi, page_tables
    mov ecx, 0x3000
    xor eax, eax
    rep stosd

    ; PML4 entry 0: point to PDPT
    mov eax, pdpt_base | 3
    mov [pml4_base], eax

    ; PML4 entry 256: kernel high half (0xFFFF_8000_0000_0000)
    mov eax, pdpt_base | 3
    mov [pml4_base + 256*8], eax

    ; PDPT entry 0: point to page directory
    mov eax, pd_base | 3
    mov [pdpt_base], eax

    ; PD entry: large 2MB page
    ; Maps 0x0000_0000 - 0x0020_0000
    mov eax, 0 | (1 << 7) | 3  ; Present, Writable, Large (2MB)
    mov [pd_base], eax

    ; Load CR3 with page table base
    mov eax, pml4_base
    mov cr3, eax

    ; Enable PAE (Physical Address Extension)
    mov eax, cr4
    or eax, 1 << 5
    mov cr4, eax

    ; Enable long mode
    mov ecx, 0xc0000080        ; IA32_EFER MSR
    rdmsr
    or eax, 1 << 8             ; LM flag
    wrmsr

    ; Enable paging (activates long mode)
    mov eax, cr0
    or eax, 1 << 31            ; PG flag
    mov cr0, eax

    ; Far jump to 64-bit code
    jmp 0x08:start_64bit

no_long_mode:
    ; CPU doesn't support long mode
    mov al, 'E'
    jmp halt

; ============================================================================
; 64-BIT LONG MODE (ACTUAL BARE-METAL KERNEL)
; ============================================================================

ALIGN 16
bits 64
start_64bit:
    ; We're now in 64-bit mode at ring-0
    ; Paging is enabled
    ; Interrupts are disabled
    ; We own the entire CPU

    ; Set up 64-bit stack
    mov rsp, stack_top_64

    ; Clear BSS section (uninitialized data)
    mov rdi, bss_start
    mov rcx, bss_size
    xor eax, eax
    rep stosb

    ; Save multiboot info pointer (in EBX before mode switch)
    ; Note: Need to restore from before 32-bit mode
    ; For now, we'll pass it to C runtime
    mov rdi, multiboot_info    ; RDI = arg0 for C calling convention

    ; Call C runtime initialization
    call kentsystem_init

    ; If we return from C runtime, halt
    jmp halt_64

; ============================================================================
; INTERRUPT DESCRIPTOR TABLE (IDT) - Exception/interrupt handlers
; ============================================================================

ALIGN 16
idt:
    ; We'll fill this in from C code (kentsystem_init)
    ; Reserve space for 256 interrupt handlers
    times 256 dq 0

idt_ptr:
    dw 256*16 - 1              ; IDT size
    dq idt                     ; IDT address

; ============================================================================
; PAGE TABLES (pre-allocated, filled in during boot)
; ============================================================================

ALIGN 4096
page_tables:
pml4_base equ page_tables + 0x0000  ; Level 4 page table (top)
pdpt_base equ page_tables + 0x1000  ; Level 3 page table (PDPT)
pd_base equ page_tables + 0x2000    ; Level 2 page table (directory)
                                     ; Level 1 page table not needed for 2MB pages

; ============================================================================
; RUNTIME STACK (grows downward)
; ============================================================================

ALIGN 4096
stack:
    times 4096 db 0
stack_top:

ALIGN 4096
stack_64:
    times 8192 db 0
stack_top_64:

; ============================================================================
; BSS SECTION (cleared by boot code)
; ============================================================================

bss_start equ stack_top_64 + 8192
bss_size equ 0x10000          ; 64KB of uninitialized data

; ============================================================================
; SIMPLE HALT ROUTINE
; ============================================================================

halt:
    mov al, 'X'
    ; Write to serial port (0x3F8 + 0 = THR)
    mov dx, 0x3F8
    out dx, al
    jmp halt

halt_64:
    cli
    hlt
    jmp halt_64

; ============================================================================
; MULTIBOOT INFO STRUCTURE (filled by bootloader)
; ============================================================================

ALIGN 8
multiboot_info: dq 0           ; Will be set by bootloader in EBX
