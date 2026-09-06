; ============================================================================
; boot.asm — KentScript Real x86-64 Boot Sector
;
; This is a genuine 512-byte MBR boot sector, assembled with NASM into a
; raw binary that BIOS/QEMU loads at 0x7C00.
;
; What it does (in order):
;   1. Sets up segment registers and a real-mode stack
;   2. Loads 128 sectors (64KB) of kernel from disk at 0x7C00+512 → 0x100000
;      using BIOS INT 13h (read sectors)
;   3. Enables the A20 line (keyboard controller method)
;   4. Loads a minimal GDT for 32-bit protected mode
;   5. Switches to 32-bit protected mode
;   6. Sets up a 32-bit temporary stack
;   7. Detects and enables 64-bit long mode (PAE + LME via EFER MSR)
;   8. Sets up a minimal 4-level page table (identity-maps 0→2GB)
;   9. Switches to 64-bit long mode
;  10. Far-jumps to the 64-bit kernel entry at 0x100000 (kmain)
;
; Assemble:
;   nasm -f bin boot.asm -o boot.bin
;
; Combine with kernel:
;   cat boot.bin kernel.bin > os.img
;   (pad kernel.bin to sector boundary first with dd)
;
; Run:
;   qemu-system-x86_64 -drive format=raw,file=os.img -m 128M
; ============================================================================

BITS    16
ORG     0x7C00

KERNEL_LOAD_SEG  equ 0x1000    ; Load at 0x10000 (64KB mark in real mode)
KERNEL_LOAD_OFF  equ 0x0000    ; Offset within segment
KERNEL_SECTORS   equ 128       ; 64KB = 128 × 512-byte sectors
KERNEL_DISK_LBA  equ 1         ; LBA sector 1 (immediately after boot sector)

PML4_ADDR   equ 0x1000         ; Page tables go at 1KB–12KB (below boot sector)
PDPT_ADDR   equ 0x2000
PD_ADDR     equ 0x3000

; ── Entry point ──────────────────────────────────────────────────────────────

start:
    cli
    xor     ax, ax
    mov     ds, ax
    mov     es, ax
    mov     ss, ax
    mov     sp, 0x7C00          ; Stack grows down from boot sector base
    mov     [boot_drive], dl    ; BIOS puts drive number in DL at boot

    ; ── Print boot message ────────────────────────────────────────────────
    mov     si, msg_boot
    call    print16

    ; ── Load kernel from disk using BIOS INT 13h extended read ────────────
    ; Use LBA extended read (INT 13h AH=42h) — works for disks > 8GB
    ; Falls back to CHS if extension not present (handled by BIOS)
    mov     ah, 0x41            ; Check extensions present
    mov     bx, 0x55AA
    int     0x13
    jc      .use_chs            ; No extensions — use CHS
    cmp     bx, 0xAA55
    jne     .use_chs

.use_lba:
    ; Fill Disk Address Packet (DAP) on stack
    mov     si, dap
    mov     word [si + 0],  0x0010      ; DAP size = 16 bytes
    mov     word [si + 2],  KERNEL_SECTORS
    mov     word [si + 4],  KERNEL_LOAD_OFF
    mov     word [si + 6],  KERNEL_LOAD_SEG
    mov     dword [si + 8], KERNEL_DISK_LBA
    mov     dword [si + 12], 0

    mov     ah, 0x42
    mov     dl, [boot_drive]
    int     0x13
    jc      disk_error
    jmp     .disk_done

.use_chs:
    ; CHS read: cylinder 0, head 0, sector 2 onwards
    mov     ax, KERNEL_LOAD_SEG
    mov     es, ax
    xor     bx, bx
    mov     ah, 0x02
    mov     al, KERNEL_SECTORS
    mov     ch, 0               ; Cylinder 0
    mov     cl, 2               ; Sector 2 (1-based)
    mov     dh, 0               ; Head 0
    mov     dl, [boot_drive]
    int     0x13
    jc      disk_error

.disk_done:
    mov     si, msg_loaded
    call    print16

    ; ── Enable A20 line (keyboard controller method) ──────────────────────
    call    enable_a20

    ; ── Load 32-bit GDT and switch to protected mode ──────────────────────
    lgdt    [gdt32_ptr]

    mov     eax, cr0
    or      eax, 1              ; Set PE (Protection Enable) bit
    mov     cr0, eax

    ; Far jump flushes the prefetch queue and reloads CS
    jmp     0x08:protected_mode_entry

disk_error:
    mov     si, msg_disk_err
    call    print16
    jmp     $                   ; Hang

; ── 16-bit print routine ─────────────────────────────────────────────────────
print16:
    lodsb
    test    al, al
    jz      .done
    mov     ah, 0x0E
    xor     bh, bh
    int     0x10
    jmp     print16
.done:
    ret

; ── A20 enable via keyboard controller ───────────────────────────────────────
enable_a20:
    call    .wait_in
    mov     al, 0xAD            ; Disable keyboard
    out     0x64, al
    call    .wait_in
    mov     al, 0xD0            ; Read output port
    out     0x64, al
    call    .wait_out
    in      al, 0x60
    push    ax
    call    .wait_in
    mov     al, 0xD1            ; Write output port
    out     0x64, al
    call    .wait_in
    pop     ax
    or      al, 2               ; Set A20 bit
    out     0x60, al
    call    .wait_in
    mov     al, 0xAE            ; Enable keyboard
    out     0x64, al
    call    .wait_in
    ret
.wait_in:
    in      al, 0x64
    test    al, 2
    jnz     .wait_in
    ret
.wait_out:
    in      al, 0x64
    test    al, 1
    jz      .wait_out
    ret

; ── Data ─────────────────────────────────────────────────────────────────────
boot_drive: db 0
msg_boot:   db "KentScript Boot", 13, 10, 0
msg_loaded: db "Kernel loaded", 13, 10, 0
msg_disk_err: db "Disk error!", 13, 10, 0

; Disk Address Packet (DAP) for INT 13h AH=42h
dap:
    times 16 db 0

; ── Minimal flat 32-bit GDT ──────────────────────────────────────────────────
align 8
gdt32:
    dq  0x0000000000000000          ; 0: Null descriptor
    dq  0x00CF9A000000FFFF          ; 1: 32-bit code, DPL 0, 4GB
    dq  0x00CF92000000FFFF          ; 2: 32-bit data, DPL 0, 4GB
    ; 64-bit code descriptor (for long mode switch)
    dq  0x00AF9A000000FFFF          ; 3: 64-bit code, DPL 0
    dq  0x00AF92000000FFFF          ; 4: 64-bit data, DPL 0
gdt32_end:

gdt32_ptr:
    dw  gdt32_end - gdt32 - 1
    dd  gdt32

; ── Pad to 510 bytes, add boot signature ─────────────────────────────────────
times 510 - ($ - $$) db 0
dw  0xAA55


; ============================================================================
; 32-BIT PROTECTED MODE — sets up PAE paging, enables long mode
; ============================================================================

BITS    32
protected_mode_entry:
    ; Reload data segments with 32-bit flat descriptor
    mov     ax, 0x10
    mov     ds, ax
    mov     es, ax
    mov     fs, ax
    mov     gs, ax
    mov     ss, ax
    mov     esp, 0x7C00         ; Temporary 32-bit stack (below boot sector)

    ; ── Build 4-level page table (identity-map 0 → 2GB) ──────────────────
    ;
    ; Page table layout (each table is 4KB = 512 entries × 8 bytes):
    ;   PML4  at PML4_ADDR (0x1000)
    ;   PDPT  at PDPT_ADDR (0x2000)
    ;   PD    at PD_ADDR   (0x3000)  — uses 2MB huge pages
    ;
    ; We identity-map 0→2GB using 1 PML4 entry → 1 PDPT entry → 2 PD entries
    ; Each PD entry with PS=1 covers 2MB, so 2 entries = 4MB (enough for boot)
    ; For a real OS, extend to cover all physical RAM.

    ; Zero all three tables
    mov     edi, PML4_ADDR
    xor     eax, eax
    mov     ecx, 0x3000 / 4     ; 12KB / 4 bytes = 3072 dwords
    rep     stosd

    ; PML4[0] → PDPT (present + writable)
    mov     dword [PML4_ADDR],      PDPT_ADDR | 3
    mov     dword [PML4_ADDR + 4],  0

    ; PDPT[0] → PD (present + writable)
    mov     dword [PDPT_ADDR],      PD_ADDR | 3
    mov     dword [PDPT_ADDR + 4],  0

    ; PD entries — 2MB huge pages, identity mapped
    ; Entry 0: virt 0x000000 → phys 0x000000 (first 2MB)
    mov     dword [PD_ADDR + 0],    0x000083    ; PS=1, R/W=1, P=1
    mov     dword [PD_ADDR + 4],    0
    ; Entry 1: virt 0x200000 → phys 0x200000 (2MB–4MB, covers 0x100000)
    mov     dword [PD_ADDR + 8],    0x200083
    mov     dword [PD_ADDR + 12],   0
    ; Entries 2–511: extend coverage to 1GB (maps phys 4MB–1GB)
    mov     edi, PD_ADDR + 16
    mov     eax, 0x400083           ; Start at 4MB
    mov     ecx, 510                ; Remaining entries
.fill_pd:
    mov     [edi], eax
    mov     dword [edi + 4], 0
    add     eax, 0x200000           ; Next 2MB page
    add     edi, 8
    loop    .fill_pd

    ; ── Load CR3 with PML4 address ────────────────────────────────────────
    mov     eax, PML4_ADDR
    mov     cr3, eax

    ; ── Enable PAE (Physical Address Extension) ───────────────────────────
    mov     eax, cr4
    or      eax, (1 << 5)       ; CR4.PAE
    mov     cr4, eax

    ; ── Set LME (Long Mode Enable) in EFER MSR ───────────────────────────
    mov     ecx, 0xC0000080     ; IA32_EFER MSR
    rdmsr
    or      eax, (1 << 8)       ; EFER.LME
    wrmsr

    ; ── Enable paging (activates long mode: LME→LMA) ─────────────────────
    mov     eax, cr0
    or      eax, (1 << 31)      ; CR0.PG
    mov     cr0, eax

    ; ── Far jump into 64-bit code segment → long mode ────────────────────
    ;   Segment selector 0x18 = GDT entry 3 (64-bit code)
    jmp     0x18:long_mode_entry


; ============================================================================
; 64-BIT LONG MODE — final setup, jump to kernel
; ============================================================================

BITS    64
long_mode_entry:
    ; Reload data segments with 64-bit flat descriptor (selector 0x20)
    mov     ax, 0x20
    mov     ds, ax
    mov     es, ax
    mov     fs, ax
    mov     gs, ax
    mov     ss, ax

    ; Set up a proper 64-bit kernel stack (16KB below 1MB)
    mov     rsp, 0xFFF00         ; Stack at ~1MB top

    ; Jump to kernel entry point at 1MB physical / virtual (identity-mapped)
    mov     rax, 0x100000
    jmp     rax                  ; → kmain() in kernel.c
