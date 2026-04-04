#!/bin/bash
# ============================================================================
# build_kernel.sh - Compile KentScript bare-metal kernel
# ============================================================================
# 
# Requirements:
#   - nasm (assembler)
#   - gcc with -ffreestanding support
#   - ld (GNU linker)
#   - qemu-system-x86_64 (for running)
#
# Usage:
#   ./build_kernel.sh [run]
#
# Examples:
#   ./build_kernel.sh           # Just compile
#   ./build_kernel.sh run       # Compile and run in QEMU
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[KentScript Bare-Metal Build System]${NC}"
echo

# ============================================================================
# STEP 1: Assemble bootloader
# ============================================================================

echo -e "${YELLOW}[1/4]${NC} Assembling bootloader (boot_x86_64.asm)..."
if ! nasm -f elf64 boot_x86_64.asm -o boot.o; then
    echo -e "${RED}ERROR: Assembly failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Bootloader assembled${NC}"

# ============================================================================
# STEP 2: Compile C runtime
# ============================================================================

echo -e "${YELLOW}[2/4]${NC} Compiling C runtime (kentsystem_init.c)..."

# Flags explained:
#   -ffreestanding     : No standard library (no libc)
#   -fno-pie           : Disable position-independent executable
#   -fno-pic           : Disable position-independent code
#   -O2                : Optimize for size and speed
#   -Wall -Wextra      : Enable warnings
#   -m64               : 64-bit code
#   -mcmodel=kernel    : Kernel memory model (for high virtual addresses)
#   -mno-red-zone      : Disable red zone (required for interrupt handlers)

if ! gcc \
    -ffreestanding \
    -fno-pie \
    -fno-pic \
    -O2 \
    -Wall -Wextra \
    -m64 \
    -mcmodel=kernel \
    -mno-red-zone \
    -c kentsystem_init.c -o kentsystem_init.o; then
    echo -e "${RED}ERROR: Compilation failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ C runtime compiled${NC}"

# ============================================================================
# STEP 3: Link kernel
# ============================================================================

echo -e "${YELLOW}[3/4]${NC} Linking kernel (link.ld)..."

if ! ld -T link.ld -o kernel.elf boot.o kentsystem_init.o; then
    echo -e "${RED}ERROR: Linking failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Kernel linked${NC}"

# ============================================================================
# STEP 4: Extract raw binary (for bootloader without ELF support)
# ============================================================================

echo -e "${YELLOW}[4/4]${NC} Creating raw binary..."
if ! objcopy -O binary kernel.elf kernel.bin; then
    echo -e "${RED}ERROR: Binary extraction failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Binary created${NC}"

# ============================================================================
# BUILD COMPLETE
# ============================================================================

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "Outputs:"
echo -e "  ${YELLOW}kernel.elf${NC}  - ELF executable (for debugging)"
echo -e "  ${YELLOW}kernel.bin${NC}  - Raw binary (for bootloader)"
echo
echo -e "File sizes:"
ls -lh kernel.elf kernel.bin
echo

# ============================================================================
# OPTIONAL: Run in QEMU
# ============================================================================

if [ "$1" = "run" ]; then
    echo -e "${YELLOW}Starting QEMU emulator...${NC}"
    echo -e "${YELLOW}(Press Ctrl+A then X to exit QEMU)${NC}"
    echo
    
    # Check if qemu-system-x86_64 exists
    if ! command -v qemu-system-x86_64 &> /dev/null; then
        echo -e "${RED}ERROR: qemu-system-x86_64 not found${NC}"
        echo "Install QEMU with: sudo apt install qemu-system-x86"
        exit 1
    fi
    
    # Run QEMU with Multiboot2 loader
    qemu-system-x86_64 \
        -kernel kernel.elf \
        -serial stdio \
        -display none \
        -m 256 \
        -enable-kvm \
        -cpu host
fi
