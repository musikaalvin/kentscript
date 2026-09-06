/*
 * KentScript Ring-0 Hardware Access Module
 * [KS-RING0-MOD-001] Auto-loading kernel module for Ring-0 access
 * [KS-RING0-MOD-002] Direct hardware access from userspace via ioctl
 * [KS-RING0-MOD-003] Physical memory, port I/O, MSR operations
 * [KS-RING0-MOD-004] Cross-platform: Linux, Windows (via driver)
 * 
 * This module enables true Ring-0 operations from KentScript runtime.
 * No privilege escalation needed - kernel handles it.
 */

#define _GNU_SOURCE
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/device.h>
#include <linux/cdev.h>
#include <linux/uaccess.h>
#include <asm/io.h>
#include <asm/msr.h>
#include <asm/page.h>
#include <linux/mm.h>
#include <linux/slab.h>
#include <linux/proc_fs.h>
#include <linux/pci.h>
#include <linux/acpi.h>

MODULE_AUTHOR("KentScript");
MODULE_DESCRIPTION("Ring-0 Hardware Access for KentScript");
MODULE_LICENSE("GPL");
MODULE_VERSION("2.0");

#define DEVICE_NAME "kentscript_ring0"
#define CLASS_NAME  "kentscript"

/* Device operations */
static int major_number;
static struct class *ring0_class = NULL;
static struct device *ring0_device = NULL;

/* ioctl command codes */
#define IOCTL_READ_MEM          _IOWR('K', 1, struct ring0_mem_op)
#define IOCTL_WRITE_MEM         _IOW('K', 2, struct ring0_mem_op)
#define IOCTL_READ_PORT         _IOWR('K', 3, struct ring0_port_op)
#define IOCTL_WRITE_PORT        _IOW('K', 4, struct ring0_port_op)
#define IOCTL_READ_MSR          _IOWR('K', 5, struct ring0_msr_op)
#define IOCTL_WRITE_MSR         _IOW('K', 6, struct ring0_msr_op)
#define IOCTL_CPUID             _IOWR('K', 7, struct ring0_cpuid_op)
#define IOCTL_RDTSC             _IOR('K', 8, unsigned long long)
#define IOCTL_MFENCE            _IO('K', 9)
#define IOCTL_CLFLUSH           _IOW('K', 10, unsigned long)
#define IOCTL_ENUM_PCI          _IOR('K', 11, struct ring0_pci_enum)
#define IOCTL_MAP_PHYS          _IOWR('K', 12, struct ring0_phys_map)

/* Data structures for ioctl operations */
struct ring0_mem_op {
    unsigned long addr;
    unsigned long value;
    int size;  /* 1, 2, 4, 8 bytes */
};

struct ring0_port_op {
    unsigned short port;
    unsigned int value;
    int size;
};

struct ring0_msr_op {
    unsigned int msr;
    unsigned long value;
    int cpu;
};

struct ring0_cpuid_op {
    unsigned int leaf;
    unsigned int subleaf;
    unsigned int eax, ebx, ecx, edx;
};

struct ring0_pci_enum {
    unsigned int bus;
    unsigned int device;
    unsigned int function;
    unsigned short vendor;
    unsigned short device_id;
    unsigned int class_code;
};

struct ring0_phys_map {
    unsigned long phys_addr;
    unsigned long size;
    unsigned long *virt_addr;  /* Out: kernel VA */
};

/* ============================================================================
 * PHYSICAL MEMORY ACCESS
 * ============================================================================ */

static long ring0_read_mem(struct ring0_mem_op *op)
{
    unsigned long val = 0;
    void __iomem *vaddr;

    /* Map physical address */
    vaddr = ioremap_nocache(op->addr, op->size);
    if (!vaddr)
        return -EFAULT;

    /* Read based on size */
    switch (op->size) {
        case 1:
            val = (unsigned long)readb(vaddr);
            break;
        case 2:
            val = (unsigned long)readw(vaddr);
            break;
        case 4:
            val = (unsigned long)readl(vaddr);
            break;
        case 8:
            val = (unsigned long)readq(vaddr);
            break;
        default:
            iounmap(vaddr);
            return -EINVAL;
    }

    iounmap(vaddr);
    op->value = val;
    return 0;
}

static long ring0_write_mem(struct ring0_mem_op *op)
{
    void __iomem *vaddr;

    vaddr = ioremap_nocache(op->addr, op->size);
    if (!vaddr)
        return -EFAULT;

    switch (op->size) {
        case 1:
            writeb((unsigned char)op->value, vaddr);
            break;
        case 2:
            writew((unsigned short)op->value, vaddr);
            break;
        case 4:
            writel((unsigned int)op->value, vaddr);
            break;
        case 8:
            writeq(op->value, vaddr);
            break;
        default:
            iounmap(vaddr);
            return -EINVAL;
    }

    iounmap(vaddr);
    return 0;
}

/* ============================================================================
 * PORT I/O ACCESS (x86)
 * ============================================================================ */

static long ring0_read_port(struct ring0_port_op *op)
{
    unsigned int val = 0;

    switch (op->size) {
        case 1:
            val = (unsigned int)inb(op->port);
            break;
        case 2:
            val = (unsigned int)inw(op->port);
            break;
        case 4:
            val = inl(op->port);
            break;
        default:
            return -EINVAL;
    }

    op->value = val;
    return 0;
}

static long ring0_write_port(struct ring0_port_op *op)
{
    switch (op->size) {
        case 1:
            outb((unsigned char)op->value, op->port);
            break;
        case 2:
            outw((unsigned short)op->value, op->port);
            break;
        case 4:
            outl(op->value, op->port);
            break;
        default:
            return -EINVAL;
    }

    return 0;
}

/* ============================================================================
 * MODEL-SPECIFIC REGISTER ACCESS
 * ============================================================================ */

static long ring0_read_msr(struct ring0_msr_op *op)
{
    u64 msr_val;
    int err;

    err = rdmsr_safe_on_cpu(op->cpu, op->msr, (u32 *)&msr_val, (u32 *)&msr_val + 1);
    if (err)
        return err;

    op->value = msr_val;
    return 0;
}

static long ring0_write_msr(struct ring0_msr_op *op)
{
    return wrmsr_safe_on_cpu(op->cpu, op->msr, (u32)op->value, (u32)(op->value >> 32));
}

/* ============================================================================
 * CPU INTRINSICS
 * ============================================================================ */

static long ring0_cpuid(struct ring0_cpuid_op *op)
{
    cpuid_count(op->leaf, op->subleaf, &op->eax, &op->ebx, &op->ecx, &op->edx);
    return 0;
}

static long ring0_rdtsc(unsigned long long *tsc)
{
    *tsc = rdtsc();
    return 0;
}

static long ring0_mfence(void)
{
    asm volatile("mfence" ::: "memory");
    return 0;
}

static long ring0_clflush(unsigned long addr)
{
    clflush((void *)addr);
    return 0;
}

/* ============================================================================
 * PCI DEVICE ENUMERATION
 * ============================================================================ */

static long ring0_enum_pci(struct ring0_pci_enum *dev)
{
    struct pci_dev *pci_dev;
    int found = 0;

    for_each_pci_dev(pci_dev) {
        if (pci_dev->bus->number == dev->bus &&
            PCI_SLOT(pci_dev->devfn) == dev->device &&
            PCI_FUNC(pci_dev->devfn) == dev->function) {
            
            dev->vendor = pci_dev->vendor;
            dev->device_id = pci_dev->device;
            dev->class_code = pci_dev->class;
            found = 1;
            break;
        }
    }

    return found ? 0 : -ENODEV;
}

/* ============================================================================
 * PHYSICAL MEMORY MAPPING
 * ============================================================================ */

static long ring0_map_phys(struct ring0_phys_map *map)
{
    unsigned long vaddr;

    vaddr = (unsigned long)ioremap_nocache(map->phys_addr, map->size);
    if (!vaddr)
        return -ENOMEM;

    map->virt_addr = (unsigned long *)vaddr;
    return 0;
}

/* ============================================================================
 * DEVICE FILE OPERATIONS
 * ============================================================================ */

static long device_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    void __user *argp = (void __user *)arg;
    int ret = 0;

    switch (cmd) {
        case IOCTL_READ_MEM: {
            struct ring0_mem_op op;
            if (copy_from_user(&op, argp, sizeof(op)))
                return -EFAULT;
            ret = ring0_read_mem(&op);
            if (!ret && copy_to_user(argp, &op, sizeof(op)))
                return -EFAULT;
            break;
        }

        case IOCTL_WRITE_MEM: {
            struct ring0_mem_op op;
            if (copy_from_user(&op, argp, sizeof(op)))
                return -EFAULT;
            ret = ring0_write_mem(&op);
            break;
        }

        case IOCTL_READ_PORT: {
            struct ring0_port_op op;
            if (copy_from_user(&op, argp, sizeof(op)))
                return -EFAULT;
            ret = ring0_read_port(&op);
            if (!ret && copy_to_user(argp, &op, sizeof(op)))
                return -EFAULT;
            break;
        }

        case IOCTL_WRITE_PORT: {
            struct ring0_port_op op;
            if (copy_from_user(&op, argp, sizeof(op)))
                return -EFAULT;
            ret = ring0_write_port(&op);
            break;
        }

        case IOCTL_READ_MSR: {
            struct ring0_msr_op op;
            if (copy_from_user(&op, argp, sizeof(op)))
                return -EFAULT;
            ret = ring0_read_msr(&op);
            if (!ret && copy_to_user(argp, &op, sizeof(op)))
                return -EFAULT;
            break;
        }

        case IOCTL_WRITE_MSR: {
            struct ring0_msr_op op;
            if (copy_from_user(&op, argp, sizeof(op)))
                return -EFAULT;
            ret = ring0_write_msr(&op);
            break;
        }

        case IOCTL_CPUID: {
            struct ring0_cpuid_op op;
            if (copy_from_user(&op, argp, sizeof(op)))
                return -EFAULT;
            ret = ring0_cpuid(&op);
            if (!ret && copy_to_user(argp, &op, sizeof(op)))
                return -EFAULT;
            break;
        }

        case IOCTL_RDTSC: {
            unsigned long long tsc;
            ret = ring0_rdtsc(&tsc);
            if (!ret && copy_to_user(argp, &tsc, sizeof(tsc)))
                return -EFAULT;
            break;
        }

        case IOCTL_MFENCE:
            ret = ring0_mfence();
            break;

        case IOCTL_CLFLUSH: {
            unsigned long addr;
            if (copy_from_user(&addr, argp, sizeof(addr)))
                return -EFAULT;
            ret = ring0_clflush(addr);
            break;
        }

        case IOCTL_ENUM_PCI: {
            struct ring0_pci_enum dev;
            if (copy_from_user(&dev, argp, sizeof(dev)))
                return -EFAULT;
            ret = ring0_enum_pci(&dev);
            if (!ret && copy_to_user(argp, &dev, sizeof(dev)))
                return -EFAULT;
            break;
        }

        case IOCTL_MAP_PHYS: {
            struct ring0_phys_map map;
            if (copy_from_user(&map, argp, sizeof(map)))
                return -EFAULT;
            ret = ring0_map_phys(&map);
            if (!ret && copy_to_user(argp, &map, sizeof(map)))
                return -EFAULT;
            break;
        }

        default:
            return -ENOTTY;
    }

    return ret;
}

static struct file_operations fops = {
    .unlocked_ioctl = device_ioctl,
};

/* ============================================================================
 * MODULE INITIALIZATION
 * ============================================================================ */

static int __init ring0_init(void)
{
    /* Register character device */
    major_number = register_chrdev(0, DEVICE_NAME, &fops);
    if (major_number < 0) {
        printk(KERN_ERR "KentScript Ring0: Failed to register device\n");
        return major_number;
    }

    /* Create device class */
    ring0_class = class_create(THIS_MODULE, CLASS_NAME);
    if (IS_ERR(ring0_class)) {
        unregister_chrdev(major_number, DEVICE_NAME);
        printk(KERN_ERR "KentScript Ring0: Failed to create class\n");
        return PTR_ERR(ring0_class);
    }

    /* Create device file */
    ring0_device = device_create(ring0_class, NULL, MKDEV(major_number, 0),
                                 NULL, DEVICE_NAME);
    if (IS_ERR(ring0_device)) {
        class_destroy(ring0_class);
        unregister_chrdev(major_number, DEVICE_NAME);
        printk(KERN_ERR "KentScript Ring0: Failed to create device\n");
        return PTR_ERR(ring0_device);
    }

    printk(KERN_INFO "KentScript Ring-0 Hardware Access Module Loaded\n");
    printk(KERN_INFO "Device: /dev/%s (major %d)\n", DEVICE_NAME, major_number);

    return 0;
}

static void __exit ring0_exit(void)
{
    device_destroy(ring0_class, MKDEV(major_number, 0));
    class_destroy(ring0_class);
    unregister_chrdev(major_number, DEVICE_NAME);

    printk(KERN_INFO "KentScript Ring-0 Module Unloaded\n");
}

module_init(ring0_init);
module_exit(ring0_exit);
