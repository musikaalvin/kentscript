/* ============================================================================
 * ks_isr_stubs.S — x86-64 ISR Entry Points for KentScript Kernel
 *
 * Two entry paths:
 *   ks_isr_common_exc  — CPU exceptions (vectors 0–31): call C handler, iretq
 *   ks_isr_common_irq  — Hardware IRQs  (vectors 32+):  call C handler,
 *                         send PIC EOI, iretq
 *
 * Stack layout on entry to common handler (after 15 GPR pushes = 120 bytes):
 *   [rsp+  0]  r15
 *   [rsp+  8]  r14
 *   [rsp+ 16]  r13
 *   [rsp+ 24]  r12
 *   [rsp+ 32]  r11
 *   [rsp+ 40]  r10
 *   [rsp+ 48]  r9
 *   [rsp+ 56]  r8
 *   [rsp+ 64]  rbp
 *   [rsp+ 72]  rdi
 *   [rsp+ 80]  rsi
 *   [rsp+ 88]  rdx
 *   [rsp+ 96]  rcx
 *   [rsp+104]  rbx
 *   [rsp+112]  rax
 *   [rsp+120]  vector number   (pushed by stub)
 *   [rsp+128]  error code      (pushed by stub or CPU)
 *   [rsp+136]  RIP             \
 *   [rsp+144]  CS               > CPU exception frame
 *   [rsp+152]  RFLAGS          /
 *   [rsp+160]  RSP (old)       \  only present on privilege-level change
 *   [rsp+168]  SS              /
 *
 * C prototypes:
 *   void ks_exception_handler(uint64_t vec, uint64_t ec, uint64_t *frame);
 *   void ks_irq_handler(uint64_t irq, uint64_t *frame);   // irq = vec - 32
 *
 * PIC I/O ports:
 *   Master PIC command: 0x20   Slave PIC command: 0xA0
 *   EOI command byte:   0x20
 * ============================================================================ */

.code64

/* ── Macros ─────────────────────────────────────────────────────────────── */

/* Exception WITHOUT CPU-pushed error code */
.macro ISR_NOERR_EXC num
.global ks_isr_\num
ks_isr_\num:
    pushq   $0
    pushq   $\num
    jmp     ks_isr_common_exc
.endm

/* Exception WITH CPU-pushed error code */
.macro ISR_ERR_EXC num
.global ks_isr_\num
ks_isr_\num:
    pushq   $\num
    jmp     ks_isr_common_exc
.endm

/* Hardware IRQ (no error code) */
.macro ISR_IRQ num
.global ks_isr_\num
ks_isr_\num:
    pushq   $0
    pushq   $\num
    jmp     ks_isr_common_irq
.endm

/* ── Exception stubs (vectors 0–31) ─────────────────────────────────────── */

ISR_NOERR_EXC 0    /* #DE  Divide Error                  */
ISR_NOERR_EXC 1    /* #DB  Debug                         */
ISR_NOERR_EXC 2    /* NMI  Non-Maskable Interrupt         */
ISR_NOERR_EXC 3    /* #BP  Breakpoint                    */
ISR_NOERR_EXC 4    /* #OF  Overflow                      */
ISR_NOERR_EXC 5    /* #BR  Bound Range Exceeded           */
ISR_NOERR_EXC 6    /* #UD  Invalid Opcode                */
ISR_NOERR_EXC 7    /* #NM  Device Not Available           */
ISR_ERR_EXC   8    /* #DF  Double Fault          (ec)    */
ISR_NOERR_EXC 9    /* -    Coprocessor Segment Overrun    */
ISR_ERR_EXC   10   /* #TS  Invalid TSS           (ec)    */
ISR_ERR_EXC   11   /* #NP  Segment Not Present   (ec)    */
ISR_ERR_EXC   12   /* #SS  Stack-Segment Fault   (ec)    */
ISR_ERR_EXC   13   /* #GP  General Protection    (ec)    */
ISR_ERR_EXC   14   /* #PF  Page Fault            (ec)    */
ISR_NOERR_EXC 15   /* -    Reserved                      */
ISR_NOERR_EXC 16   /* #MF  x87 FPU Error                 */
ISR_ERR_EXC   17   /* #AC  Alignment Check       (ec)    */
ISR_NOERR_EXC 18   /* #MC  Machine Check                 */
ISR_NOERR_EXC 19   /* #XM  SIMD FP Exception             */
ISR_NOERR_EXC 20   /* #VE  Virtualization Exception       */
ISR_ERR_EXC   21   /* #CP  Control Protection    (ec)    */
ISR_NOERR_EXC 22
ISR_NOERR_EXC 23
ISR_NOERR_EXC 24
ISR_NOERR_EXC 25
ISR_NOERR_EXC 26
ISR_NOERR_EXC 27
ISR_NOERR_EXC 28   /* #HV  Hypervisor Injection          */
ISR_ERR_EXC   29   /* #VC  VMM Communication     (ec)    */
ISR_ERR_EXC   30   /* #SX  Security Exception    (ec)    */
ISR_NOERR_EXC 31

/* ── IRQ stubs (vectors 32–255) ─────────────────────────────────────────── */

ISR_IRQ 32   /* IRQ0  PIT timer            */
ISR_IRQ 33   /* IRQ1  PS/2 keyboard        */
ISR_IRQ 34   /* IRQ2  cascade              */
ISR_IRQ 35   /* IRQ3  COM2                 */
ISR_IRQ 36   /* IRQ4  COM1                 */
ISR_IRQ 37   /* IRQ5  LPT2                 */
ISR_IRQ 38   /* IRQ6  floppy               */
ISR_IRQ 39   /* IRQ7  LPT1 / spurious      */
ISR_IRQ 40   /* IRQ8  RTC                  */
ISR_IRQ 41   /* IRQ9  ACPI                 */
ISR_IRQ 42   /* IRQ10 free                 */
ISR_IRQ 43   /* IRQ11 free                 */
ISR_IRQ 44   /* IRQ12 PS/2 mouse           */
ISR_IRQ 45   /* IRQ13 FPU                  */
ISR_IRQ 46   /* IRQ14 ATA primary          */
ISR_IRQ 47   /* IRQ15 ATA secondary        */

ISR_IRQ 48;  ISR_IRQ 49;  ISR_IRQ 50;  ISR_IRQ 51
ISR_IRQ 52;  ISR_IRQ 53;  ISR_IRQ 54;  ISR_IRQ 55
ISR_IRQ 56;  ISR_IRQ 57;  ISR_IRQ 58;  ISR_IRQ 59
ISR_IRQ 60;  ISR_IRQ 61;  ISR_IRQ 62;  ISR_IRQ 63
ISR_IRQ 64;  ISR_IRQ 65;  ISR_IRQ 66;  ISR_IRQ 67
ISR_IRQ 68;  ISR_IRQ 69;  ISR_IRQ 70;  ISR_IRQ 71
ISR_IRQ 72;  ISR_IRQ 73;  ISR_IRQ 74;  ISR_IRQ 75
ISR_IRQ 76;  ISR_IRQ 77;  ISR_IRQ 78;  ISR_IRQ 79
ISR_IRQ 80;  ISR_IRQ 81;  ISR_IRQ 82;  ISR_IRQ 83
ISR_IRQ 84;  ISR_IRQ 85;  ISR_IRQ 86;  ISR_IRQ 87
ISR_IRQ 88;  ISR_IRQ 89;  ISR_IRQ 90;  ISR_IRQ 91
ISR_IRQ 92;  ISR_IRQ 93;  ISR_IRQ 94;  ISR_IRQ 95
ISR_IRQ 96;  ISR_IRQ 97;  ISR_IRQ 98;  ISR_IRQ 99
ISR_IRQ 100; ISR_IRQ 101; ISR_IRQ 102; ISR_IRQ 103
ISR_IRQ 104; ISR_IRQ 105; ISR_IRQ 106; ISR_IRQ 107
ISR_IRQ 108; ISR_IRQ 109; ISR_IRQ 110; ISR_IRQ 111
ISR_IRQ 112; ISR_IRQ 113; ISR_IRQ 114; ISR_IRQ 115
ISR_IRQ 116; ISR_IRQ 117; ISR_IRQ 118; ISR_IRQ 119
ISR_IRQ 120; ISR_IRQ 121; ISR_IRQ 122; ISR_IRQ 123
ISR_IRQ 124; ISR_IRQ 125; ISR_IRQ 126; ISR_IRQ 127
ISR_IRQ 128; ISR_IRQ 129; ISR_IRQ 130; ISR_IRQ 131
ISR_IRQ 132; ISR_IRQ 133; ISR_IRQ 134; ISR_IRQ 135
ISR_IRQ 136; ISR_IRQ 137; ISR_IRQ 138; ISR_IRQ 139
ISR_IRQ 140; ISR_IRQ 141; ISR_IRQ 142; ISR_IRQ 143
ISR_IRQ 144; ISR_IRQ 145; ISR_IRQ 146; ISR_IRQ 147
ISR_IRQ 148; ISR_IRQ 149; ISR_IRQ 150; ISR_IRQ 151
ISR_IRQ 152; ISR_IRQ 153; ISR_IRQ 154; ISR_IRQ 155
ISR_IRQ 156; ISR_IRQ 157; ISR_IRQ 158; ISR_IRQ 159
ISR_IRQ 160; ISR_IRQ 161; ISR_IRQ 162; ISR_IRQ 163
ISR_IRQ 164; ISR_IRQ 165; ISR_IRQ 166; ISR_IRQ 167
ISR_IRQ 168; ISR_IRQ 169; ISR_IRQ 170; ISR_IRQ 171
ISR_IRQ 172; ISR_IRQ 173; ISR_IRQ 174; ISR_IRQ 175
ISR_IRQ 176; ISR_IRQ 177; ISR_IRQ 178; ISR_IRQ 179
ISR_IRQ 180; ISR_IRQ 181; ISR_IRQ 182; ISR_IRQ 183
ISR_IRQ 184; ISR_IRQ 185; ISR_IRQ 186; ISR_IRQ 187
ISR_IRQ 188; ISR_IRQ 189; ISR_IRQ 190; ISR_IRQ 191
ISR_IRQ 192; ISR_IRQ 193; ISR_IRQ 194; ISR_IRQ 195
ISR_IRQ 196; ISR_IRQ 197; ISR_IRQ 198; ISR_IRQ 199
ISR_IRQ 200; ISR_IRQ 201; ISR_IRQ 202; ISR_IRQ 203
ISR_IRQ 204; ISR_IRQ 205; ISR_IRQ 206; ISR_IRQ 207
ISR_IRQ 208; ISR_IRQ 209; ISR_IRQ 210; ISR_IRQ 211
ISR_IRQ 212; ISR_IRQ 213; ISR_IRQ 214; ISR_IRQ 215
ISR_IRQ 216; ISR_IRQ 217; ISR_IRQ 218; ISR_IRQ 219
ISR_IRQ 220; ISR_IRQ 221; ISR_IRQ 222; ISR_IRQ 223
ISR_IRQ 224; ISR_IRQ 225; ISR_IRQ 226; ISR_IRQ 227
ISR_IRQ 228; ISR_IRQ 229; ISR_IRQ 230; ISR_IRQ 231
ISR_IRQ 232; ISR_IRQ 233; ISR_IRQ 234; ISR_IRQ 235
ISR_IRQ 236; ISR_IRQ 237; ISR_IRQ 238; ISR_IRQ 239
ISR_IRQ 240; ISR_IRQ 241; ISR_IRQ 242; ISR_IRQ 243
ISR_IRQ 244; ISR_IRQ 245; ISR_IRQ 246; ISR_IRQ 247
ISR_IRQ 248; ISR_IRQ 249; ISR_IRQ 250; ISR_IRQ 251
ISR_IRQ 252; ISR_IRQ 253; ISR_IRQ 254; ISR_IRQ 255

/* ── GPR save/restore helpers ───────────────────────────────────────────── */

.macro SAVE_REGS
    pushq   %rax
    pushq   %rbx
    pushq   %rcx
    pushq   %rdx
    pushq   %rsi
    pushq   %rdi
    pushq   %rbp
    pushq   %r8
    pushq   %r9
    pushq   %r10
    pushq   %r11
    pushq   %r12
    pushq   %r13
    pushq   %r14
    pushq   %r15
.endm

.macro RESTORE_REGS
    popq    %r15
    popq    %r14
    popq    %r13
    popq    %r12
    popq    %r11
    popq    %r10
    popq    %r9
    popq    %r8
    popq    %rbp
    popq    %rdi
    popq    %rsi
    popq    %rdx
    popq    %rcx
    popq    %rbx
    popq    %rax
.endm

/* ── Exception dispatcher ───────────────────────────────────────────────── */
/*
 * Calls: void ks_exception_handler(uint64_t vec, uint64_t ec, uint64_t *frame)
 * If the handler returns, we iretq (handler resolved the fault).
 * Non-returning exceptions (#DF, #MC, NMI) should not return from C.
 */
.global ks_isr_common_exc
ks_isr_common_exc:
    SAVE_REGS

    movq    120(%rsp), %rdi     /* vec   */
    movq    128(%rsp), %rsi     /* ec    */
    leaq    136(%rsp), %rdx     /* frame */

    /* Stack is 8-byte misaligned here (odd number of 8-byte pushes since
     * last 16-byte boundary before the interrupt).  The call instruction
     * pushes the return address (8 bytes), making it 16-byte aligned at
     * function entry — no manual alignment needed. */
    call    ks_exception_handler

    RESTORE_REGS
    addq    $16, %rsp           /* discard vec + ec */
    iretq

/* ── IRQ dispatcher ─────────────────────────────────────────────────────── */
/*
 * Calls: void ks_irq_handler(uint64_t irq, uint64_t *frame)
 *   irq = vector - 32  (so IRQ0 = 0, IRQ1 = 1, …)
 *
 * After the C handler returns, sends EOI to the 8259 PIC:
 *   - All IRQs:        EOI to master PIC (port 0x20)
 *   - IRQs 8–15:       EOI to slave PIC  (port 0xA0) first
 */
.global ks_isr_common_irq
ks_isr_common_irq:
    SAVE_REGS

    movq    120(%rsp), %rdi     /* vector number */
    subq    $32, %rdi           /* convert to IRQ number (0-based) */
    leaq    136(%rsp), %rsi     /* frame */

    call    ks_irq_handler

    /* Send EOI — read vector back from stack (now at [rsp+120]) */
    movq    120(%rsp), %rax     /* vector */

    /* If vector >= 40 (IRQ8+), send EOI to slave PIC first */
    cmpq    $40, %rax
    jl      .Lmaster_eoi
    movb    $0x20, %al
    outb    %al, $0xA0          /* slave PIC EOI */

.Lmaster_eoi:
    movb    $0x20, %al
    outb    %al, $0x20          /* master PIC EOI */

    RESTORE_REGS
    addq    $16, %rsp           /* discard vec + dummy ec */
    iretq

/* ── ISR address table ──────────────────────────────────────────────────── */
.section .rodata
.global ks_isr_table
ks_isr_table:
    .quad ks_isr_0;   .quad ks_isr_1;   .quad ks_isr_2;   .quad ks_isr_3
    .quad ks_isr_4;   .quad ks_isr_5;   .quad ks_isr_6;   .quad ks_isr_7
    .quad ks_isr_8;   .quad ks_isr_9;   .quad ks_isr_10;  .quad ks_isr_11
    .quad ks_isr_12;  .quad ks_isr_13;  .quad ks_isr_14;  .quad ks_isr_15
    .quad ks_isr_16;  .quad ks_isr_17;  .quad ks_isr_18;  .quad ks_isr_19
    .quad ks_isr_20;  .quad ks_isr_21;  .quad ks_isr_22;  .quad ks_isr_23
    .quad ks_isr_24;  .quad ks_isr_25;  .quad ks_isr_26;  .quad ks_isr_27
    .quad ks_isr_28;  .quad ks_isr_29;  .quad ks_isr_30;  .quad ks_isr_31
    .quad ks_isr_32;  .quad ks_isr_33;  .quad ks_isr_34;  .quad ks_isr_35
    .quad ks_isr_36;  .quad ks_isr_37;  .quad ks_isr_38;  .quad ks_isr_39
    .quad ks_isr_40;  .quad ks_isr_41;  .quad ks_isr_42;  .quad ks_isr_43
    .quad ks_isr_44;  .quad ks_isr_45;  .quad ks_isr_46;  .quad ks_isr_47
    .quad ks_isr_48;  .quad ks_isr_49;  .quad ks_isr_50;  .quad ks_isr_51
    .quad ks_isr_52;  .quad ks_isr_53;  .quad ks_isr_54;  .quad ks_isr_55
    .quad ks_isr_56;  .quad ks_isr_57;  .quad ks_isr_58;  .quad ks_isr_59
    .quad ks_isr_60;  .quad ks_isr_61;  .quad ks_isr_62;  .quad ks_isr_63
    .quad ks_isr_64;  .quad ks_isr_65;  .quad ks_isr_66;  .quad ks_isr_67
    .quad ks_isr_68;  .quad ks_isr_69;  .quad ks_isr_70;  .quad ks_isr_71
    .quad ks_isr_72;  .quad ks_isr_73;  .quad ks_isr_74;  .quad ks_isr_75
    .quad ks_isr_76;  .quad ks_isr_77;  .quad ks_isr_78;  .quad ks_isr_79
    .quad ks_isr_80;  .quad ks_isr_81;  .quad ks_isr_82;  .quad ks_isr_83
    .quad ks_isr_84;  .quad ks_isr_85;  .quad ks_isr_86;  .quad ks_isr_87
    .quad ks_isr_88;  .quad ks_isr_89;  .quad ks_isr_90;  .quad ks_isr_91
    .quad ks_isr_92;  .quad ks_isr_93;  .quad ks_isr_94;  .quad ks_isr_95
    .quad ks_isr_96;  .quad ks_isr_97;  .quad ks_isr_98;  .quad ks_isr_99
    .quad ks_isr_100; .quad ks_isr_101; .quad ks_isr_102; .quad ks_isr_103
    .quad ks_isr_104; .quad ks_isr_105; .quad ks_isr_106; .quad ks_isr_107
    .quad ks_isr_108; .quad ks_isr_109; .quad ks_isr_110; .quad ks_isr_111
    .quad ks_isr_112; .quad ks_isr_113; .quad ks_isr_114; .quad ks_isr_115
    .quad ks_isr_116; .quad ks_isr_117; .quad ks_isr_118; .quad ks_isr_119
    .quad ks_isr_120; .quad ks_isr_121; .quad ks_isr_122; .quad ks_isr_123
    .quad ks_isr_124; .quad ks_isr_125; .quad ks_isr_126; .quad ks_isr_127
    .quad ks_isr_128; .quad ks_isr_129; .quad ks_isr_130; .quad ks_isr_131
    .quad ks_isr_132; .quad ks_isr_133; .quad ks_isr_134; .quad ks_isr_135
    .quad ks_isr_136; .quad ks_isr_137; .quad ks_isr_138; .quad ks_isr_139
    .quad ks_isr_140; .quad ks_isr_141; .quad ks_isr_142; .quad ks_isr_143
    .quad ks_isr_144; .quad ks_isr_145; .quad ks_isr_146; .quad ks_isr_147
    .quad ks_isr_148; .quad ks_isr_149; .quad ks_isr_150; .quad ks_isr_151
    .quad ks_isr_152; .quad ks_isr_153; .quad ks_isr_154; .quad ks_isr_155
    .quad ks_isr_156; .quad ks_isr_157; .quad ks_isr_158; .quad ks_isr_159
    .quad ks_isr_160; .quad ks_isr_161; .quad ks_isr_162; .quad ks_isr_163
    .quad ks_isr_164; .quad ks_isr_165; .quad ks_isr_166; .quad ks_isr_167
    .quad ks_isr_168; .quad ks_isr_169; .quad ks_isr_170; .quad ks_isr_171
    .quad ks_isr_172; .quad ks_isr_173; .quad ks_isr_174; .quad ks_isr_175
    .quad ks_isr_176; .quad ks_isr_177; .quad ks_isr_178; .quad ks_isr_179
    .quad ks_isr_180; .quad ks_isr_181; .quad ks_isr_182; .quad ks_isr_183
    .quad ks_isr_184; .quad ks_isr_185; .quad ks_isr_186; .quad ks_isr_187
    .quad ks_isr_188; .quad ks_isr_189; .quad ks_isr_190; .quad ks_isr_191
    .quad ks_isr_192; .quad ks_isr_193; .quad ks_isr_194; .quad ks_isr_195
    .quad ks_isr_196; .quad ks_isr_197; .quad ks_isr_198; .quad ks_isr_199
    .quad ks_isr_200; .quad ks_isr_201; .quad ks_isr_202; .quad ks_isr_203
    .quad ks_isr_204; .quad ks_isr_205; .quad ks_isr_206; .quad ks_isr_207
    .quad ks_isr_208; .quad ks_isr_209; .quad ks_isr_210; .quad ks_isr_211
    .quad ks_isr_212; .quad ks_isr_213; .quad ks_isr_214; .quad ks_isr_215
    .quad ks_isr_216; .quad ks_isr_217; .quad ks_isr_218; .quad ks_isr_219
    .quad ks_isr_220; .quad ks_isr_221; .quad ks_isr_222; .quad ks_isr_223
    .quad ks_isr_224; .quad ks_isr_225; .quad ks_isr_226; .quad ks_isr_227
    .quad ks_isr_228; .quad ks_isr_229; .quad ks_isr_230; .quad ks_isr_231
    .quad ks_isr_232; .quad ks_isr_233; .quad ks_isr_234; .quad ks_isr_235
    .quad ks_isr_236; .quad ks_isr_237; .quad ks_isr_238; .quad ks_isr_239
    .quad ks_isr_240; .quad ks_isr_241; .quad ks_isr_242; .quad ks_isr_243
    .quad ks_isr_244; .quad ks_isr_245; .quad ks_isr_246; .quad ks_isr_247
    .quad ks_isr_248; .quad ks_isr_249; .quad ks_isr_250; .quad ks_isr_251
    .quad ks_isr_252; .quad ks_isr_253; .quad ks_isr_254; .quad ks_isr_255
