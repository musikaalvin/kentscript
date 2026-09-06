# MiniOS SMP Support - Multi-core processors

MINIOS_SMP_C = r"""
/* ================================================================
 * MiniOS SMP Support - Multi-core Processor Support
 * ================================================================
 * Features:
 * - Per-CPU runqueues
 * - CPU bringup for secondary cores
 * - CPU affinity
 * - Load balancing
 * - CPU hotplug (stub)
 * - SMP-safe data structures
 * ================================================================ */

/* ================================================================ CPU STRUCTURE */
#define MAX_CPUS 8

typedef struct {
    int id;
    int online;
    u64 ticks;
    u64 ctx_switches;
    u64 idle_time;
    int current_task;
    u64 last_resched;
} cpu_info_t;

static cpu_info_t cpus[MAX_CPUS];
static int num_online_cpus=1;
static int boot_cpu=0;
static spinlock_t cpu_lock=0;

/* Per-CPU data - use tp (Thread Pointer) to access */
#define PER_CPU_OFFSET(id, var) ((char*)&var + (id * 4096))

/* ================================================================ SECONDARY CPU BOOT */
#define CPU_BOOT_STACK_SIZE 16384
static u8 secondary_stacks[MAX_CPUS][CPU_BOOT_STACK_SIZE] __attribute__((aligned(16)));

/* Secondary CPU entry point - called from assembly */
extern void secondary_start(void);
extern void smp_init_complete(void);

/* Park secondary cores until ready */
static void park_secondary_cores(void){
    for(int i=1;i<MAX_CPUS;i++){
        cpus[i].online=0;
        cpus[i].current_task=0;
    }
}

/* ================================================================ PER-CPU RUNQUEUE */
typedef struct {
    int tasks[MAX_TASKS];
    int count;
    int head;
    int tail;
    spinlock_t lock;
} runqueue_t;

static runqueue_t per_cpu_runqueues[MAX_CPUS];

static void runqueue_init(int cpu){
    per_cpu_runqueues[cpu].count=0;
    per_cpu_runqueues[cpu].head=0;
    per_cpu_runqueues[cpu].tail=0;
    per_cpu_runqueues[cpu].lock=0;
    for(int i=0;i<MAX_TASKS;i++)per_cpu_runqueues[cpu].tasks[i]=-1;
}

static int runqueue_enqueue(int cpu, int task_id){
    if(cpu<0||cpu>=MAX_CPUS)return -1;
    spin_lock(&per_cpu_runqueues[cpu].lock);
    if(per_cpu_runqueues[cpu].count>=MAX_TASKS){
        spin_unlock(&per_cpu_runqueues[cpu].lock);
        return -1;
    }
    int pos=per_cpu_runqueues[cpu].tail;
    per_cpu_runqueues[cpu].tasks[pos]=task_id;
    per_cpu_runqueues[cpu].tail=(pos+1)%MAX_TASKS;
    per_cpu_runqueues[cpu].count++;
    spin_unlock(&per_cpu_runqueues[cpu].lock);
    return 0;
}

static int runqueue_dequeue(int cpu){
    if(cpu<0||cpu>=MAX_CPUS)return -1;
    spin_lock(&per_cpu_runqueues[cpu].lock);
    if(per_cpu_runqueues[cpu].count==0){
        spin_unlock(&per_cpu_runqueues[cpu].lock);
        return 0; /* Idle */
    }
    int pos=per_cpu_runqueues[cpu].head;
    int task_id=per_cpu_runqueues[cpu].tasks[pos];
    per_cpu_runqueues[cpu].head=(pos+1)%MAX_TASKS;
    per_cpu_runqueues[cpu].count--;
    spin_unlock(&per_cpu_runqueues[cpu].lock);
    return task_id;
}

static int runqueue_length(int cpu){
    return per_cpu_runqueues[cpu].count;
}

/* ================================================================ CPU BRINGUP */
static void bringup_cpu(int cpu_id){
    if(cpu_id<0||cpu_id>=MAX_CPUS)return;
    if(cpus[cpu_id].online)return; /* Already up */
    
    uart_puts("[SMP] Bringing up CPU ");put_dec((u64)cpu_id);uart_puts("\n");
    
    /* Set up secondary CPU stack */
    u64 stack_top=(u64)&secondary_stacks[cpu_id][CPU_BOOT_STACK_SIZE];
    stack_top&=~0xFUL; /* 16-byte align */
    
    /* Wake up CPU - in real HW this would use psci or spin-table */
    /* For QEMU virt, secondary cores are started by the firmware */
    
    cpus[cpu_id].online=1;
    cpus[cpu_id].id=cpu_id;
    num_online_cpus++;
    runqueue_init(cpu_id);
    
    uart_puts("[SMP] CPU ");put_dec((u64)cpu_id);uart_puts(" is now online\n");
}

static void bringup_secondary_cores(void){
    u64 mpidr;
    __asm__ volatile("mrs %0, mpidr_el1":"=r"(mpidr));
    int current_cpu=mpidr&0xFF;
    
    uart_puts("[SMP] Boot CPU: ");put_dec((u64)current_cpu);uart_puts("\n");
    cpus[current_cpu].online=1;
    cpus[current_cpu].id=current_cpu;
    
    /* Detect number of available CPUs */
    /* In real HW, we'd query the device tree or ACPI tables */
    /* For QEMU virt with -smp N, we have N cores */
    int possible_cpus=1; /* Default */
    
    uart_puts("[SMP] Possible CPUs: ");put_dec((u64)possible_cpus);uart_puts("\n");
    
    /* Bring up detected CPUs (simplified) */
    for(int i=0;i<possible_cpus;i++){
        if(i!=current_cpu){
            bringup_cpu(i);
        }
    }
    
    uart_puts("[SMP] Total online CPUs: ");put_dec((u64)num_online_cpus);uart_puts("\n");
}

/* ================================================================ CPU AFFINITY */
static cpu_set_t {
    unsigned long bits[2]; /* Support up to 64 CPUs */
} process_cpu_mask;

static void CPU_SET(int cpu, cpu_set_t *set){
    if(cpu<64)set->bits[cpu/64]|=(1UL<<(cpu%64));
}
static void CPU_CLR(int cpu, cpu_set_t *set){
    if(cpu<64)set->bits[cpu/64]&=~(1UL<<(cpu%64));
}
static int CPU_ISSET(int cpu, cpu_set_t *set){
    if(cpu<64)return (set->bits[cpu/64]>>(cpu%64))&1;
    return 0;
}
static void CPU_ZERO(cpu_set_t *set){
    set->bits[0]=set->bits[1]=0;
}

static cpu_set_t task_affinity[MAX_TASKS];

static int sched_setaffinity(pid_t pid, cpu_set_t *mask){
    if(pid<0||pid>=MAX_TASKS)return -1;
    task_affinity[pid]=*mask;
    return 0;
}

static int sched_getaffinity(pid_t pid, cpu_set_t *mask){
    if(pid<0||pid>=MAX_TASKS)return -1;
    *mask=task_affinity[pid];
    return 0;
}

/* ================================================================ LOAD BALANCING */
#define LOAD_BALANCE_INTERVAL 100 /* ticks */
static u64 last_balance=0;

static int find_least_loaded_cpu(void){
    int best_cpu=0;
    int min_load=INT_MAX;
    for(int i=0;i<num_online_cpus;i++){
        if(!cpus[i].online)continue;
        int load=runqueue_length(i);
        if(load<min_load){
            min_load=load;
            best_cpu=i;
        }
    }
    return best_cpu;
}

static void load_balance(void){
    if(tick_count-last_balance<LOAD_BALANCE_INTERVAL)return;
    last_balance=tick_count;
    
    /* Find overloaded and underloaded CPUs */
    int max_cpu=-1, min_cpu=-1;
    int max_load=0, min_load=INT_MAX;
    
    for(int i=0;i<num_online_cpus;i++){
        if(!cpus[i].online)continue;
        int load=runqueue_length(i);
        if(load>max_load){max_load=load;max_cpu=i;}
        if(load<min_load){min_load=load;min_cpu=i;}
    }
    
    /* Migrate task if imbalance is significant */
    if(max_cpu>=0&&min_cpu>=0&&max_load-min_load>2){
        int task=runqueue_dequeue(max_cpu);
        if(task>0){
            runqueue_enqueue(min_cpu,task);
            uart_puts("[SMP] Migrated task ");put_dec((u64)task);
            uart_puts(" from CPU ");put_dec((u64)max_cpu);
            uart_puts(" to CPU ");put_dec((u64)min_cpu);uart_puts("\n");
        }
    }
}

/* ================================================================ SMP-SAFE OPERATIONS */
static void smp_wmb(void){
    __asm__ volatile("dmb ishst":::"memory");
}

static void smp_rmb(void){
    __asm__ volatile("dmb ishld":::"memory");
}

static void smp_mb(void){
    __asm__ volatile("dmb ish":::"memory");
}

/* Atomic operations */
static u64 atomic_load(u64 *ptr){
    u64 val;
    __asm__ volatile("ldr %0, [%1]":"=r"(val):"r"(ptr):"memory");
    return val;
}

static void atomic_store(u64 *ptr, u64 val){
    __asm__ volatile("str %0, [%1]":"=r"(val):"r"(val),"r"(ptr):"memory");
}

static u64 atomic_add(u64 *ptr, u64 val){
    u64 result;
    __asm__ volatile(
        "1: ldxr %0, [%2]\n"
        "   add %0, %0, %1\n"
        "   stxr w3, %0, [%2]\n"
        "   cbnz w3, 1b\n"
        :"=&r"(result):"r"(val),"r"(ptr):"memory"
    );
    return result;
}

static u64 atomic_swap(u64 *ptr, u64 val){
    u64 result;
    __asm__ volatile(
        "1: ldxr %0, [%2]\n"
        "   stxr w3, %1, [%2]\n"
        "   cbnz w3, 1b\n"
        :"=&r"(result):"r"(val),"r"(ptr):"memory"
    );
    return result;
}

static int atomic_cas(u64 *ptr, u64 old, u64 new_val){
    u64 tmp;
    __asm__ volatile(
        "1: ldxr %0, [%3]\n"
        "   cmp %0, %1\n"
        "   b.ne 2f\n"
        "   stxr w2, %4, [%3]\n"
        "   cbnz w2, 1b\n"
        "2:\n"
        :"=&r"(tmp):"r"(old),"r"(new_val),"r"(ptr):"memory"
    );
    return tmp==old?0:1;
}

/* ================================================================ SMP INITIALIZATION */
static void smp_init(void){
    uart_puts("[SMP] Initializing symmetric multiprocessing...\n");
    
    /* Initialize per-CPU runqueues */
    for(int i=0;i<MAX_CPUS;i++)runqueue_init(i);
    
    /* Initialize CPU info */
    u64 mpidr;
    __asm__ volatile("mrs %0, mpidr_el1":"=r"(mpidr));
    boot_cpu=mpidr&0xFF;
    
    for(int i=0;i<MAX_CPUS;i++){
        cpus[i].id=i;
        cpus[i].online=0;
        cpus[i].ticks=0;
        cpus[i].ctx_switches=0;
        cpus[i].idle_time=0;
        cpus[i].current_task=0;
    }
    cpus[boot_cpu].online=1;
    num_online_cpus=1;
    
    /* Set up CPU affinity for init task */
    CPU_ZERO(&task_affinity[0]);
    CPU_SET(boot_cpu,&task_affinity[0]);
    
    uart_puts("[SMP] Boot CPU: ");put_dec((u64)boot_cpu);uart_puts("\n");
    
    /* In QEMU, secondary cores are started by the firmware */
    /* The kernel just needs to handle their entry points */
}

/* ================================================================ CPU HOTPLUG (stub) */
static int cpu_online(int cpu){
    if(cpu<0||cpu>=MAX_CPUS)return -1;
    return cpus[cpu].online;
}

static int cpu_up(int cpu){
    if(cpu<0||cpu>=MAX_CPUS||cpu==boot_cpu)return -1;
    bringup_cpu(cpu);
    return 0;
}

static int cpu_down(int cpu){
    if(cpu<0||cpu>=MAX_CPUS||cpu==boot_cpu)return -1;
    if(!cpus[cpu].online)return -1;
    
    uart_puts("[SMP] Taking CPU ");put_dec((u64)cpu);uart_puts(" offline\n");
    /* Migrate tasks away first */
    cpus[cpu].online=0;
    num_online_cpus--;
    return 0;
}

/* ================================================================ /proc/cpuinfo SMP */
static void show_smp_info(void){
    uart_puts("SMP: ");
    put_dec((u64)num_online_cpus);
    uart_puts(" CPUs online\n");
    for(int i=0;i<MAX_CPUS;i++){
        if(cpus[i].online){
            uart_puts("CPU");put_dec((u64)i);
            uart_puts(": online ticks=");put_dec(cpus[i].ticks);
            uart_puts(" ctx_sw=");put_dec(cpus[i].ctx_switches);
            uart_puts("\n");
        }
    }
}

/* ================================================================ INTER-CPU INTERRUPT */
#define IPI_RESCHEDULE  1
#define IPI_CALL_FUNC    2
#define IPI_CPU_STOP     3

static void send_ipi(int cpu, int ipi){
    if(cpu<0||cpu>=MAX_CPUS||!cpus[cpu].online)return;
    /* In real HW, use GICD_SGIR or PSCI */
    uart_puts("[SMP] Send IPI ");put_dec((u64)ipi);
    uart_puts(" to CPU ");put_dec((u64)cpu);uart_puts("\n");
}

static void broadcast_ipi(int ipi){
    for(int i=0;i<MAX_CPUS;i++){
        if(cpus[i].online&&i!=boot_cpu)send_ipi(i,ipi);
    }
}

/* ================================================================ THREAD-LOCAL STORAGE */
static u64 tls_base=0xFFFF000000000000ULL;

static u64 get_tls(void){
    u64 tp;
    __asm__ volatile("mrs %0, tpidr_el1":"=r"(tp));
    return tp;
}

static void set_tls(u64 val){
    __asm__ volatile("msr tpidr_el1, %0"::"r"(val):"memory");
}
"""

# Add to exports
__all__ = ["MINIOS_SMP_C"]
