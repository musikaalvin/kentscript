# MiniOS Enhanced Process Management - fork, exec, signals, ptrace

MINIOS_PROCESS_C = r"""
/* ================================================================
 * MiniOS Enhanced Process Management
 * ================================================================
 * Features:
 * - fork() - process forking
 * - execve() - replace process image
 * - wait(), waitpid() - wait for child processes
 * - kill() - send signals
 * - Signal handling (SIGTERM, SIGKILL, SIGINT, SIGCHLD, etc.)
 * - nice/renice - process priority
 * - ptrace - process tracing (basic)
 * - getuid/geteuid/getgid/getegid
 * - setuid/setgid
 * - Session and process groups
 * ================================================================ */

/* ================================================================ USER/GROUP IDs */
typedef struct {
    u32 uid;
    u32 euid;
    u32 suid;
    u32 uid_count;
} cred_t;

static cred_t root_cred={0,0,0,0};
static cred_t current_cred={0,0,0,0};

static uid_t getuid(void){return current_cred.uid;}
static uid_t geteuid(void){return current_cred.euid;}
static gid_t getgid(void){return current_cred.gid;}
static gid_t getegid(void){return current_cred.egid;}
static int setuid(uid_t uid){current_cred.uid=uid;current_cred.euid=uid;return 0;}
static int setgid(gid_t gid){current_cred.gid=gid;current_cred.egid=gid;return 0;}

/* ================================================================ SIGNAL HANDLING */
#define NSIG 32
#define SIGHUP    1
#define SIGINT    2
#define SIGQUIT   3
#define SIGILL    4
#define SIGTRAP   5
#define SIGABRT   6
#define SIGBUS    7
#define SIGFPE    8
#define SIGKILL   9
#define SIGUSR1  10
#define SIGSEGV  11
#define SIGUSR2  12
#define SIGPIPE  13
#define SIGALRM  14
#define SIGTERM  15
#define SIGSTKFLT 16
#define SIGCHLD  17
#define SIGCONT  18
#define SIGSTOP  19
#define SIGTSTP  20
#define SIGTTIN  21
#define SIGTTOU  22

typedef void (*sighandler_t)(int);
static sighandler_t signal_handlers[NSIG];
static void default_signal_handler(int sig){
    switch(sig){
        case SIGKILL:
        case SIGSTOP: return; /* Cannot be caught */
        case SIGCHLD: return; /* Ignore */
        case SIGINT: tasks[current_task].state=TASK_DEAD;break;
        case SIGTERM: tasks[current_task].state=TASK_DEAD;break;
        case SIGSEGV: 
            uart_puts("\n[PANIC] Segmentation fault!\n");
            __asm__ volatile("msr daifset, #0xf");
            while(1) __asm__ volatile("wfe");
            break;
        case SIGABRT:
            uart_puts("\n[PANIC] Aborted!\n");
            tasks[current_task].state=TASK_DEAD;
            break;
        default:
            uart_puts("\n[SIGNAL] Received signal ");put_dec((u64)sig);uart_puts("\n");
    }
}

static sighandler_t signal(int sig, sighandler_t handler){
    if(sig<0||sig>=NSIG)return (sighandler_t)-1;
    sighandler_t old=signal_handlers[sig];
    if(handler==0)signal_handlers[sig]=default_signal_handler;
    else signal_handlers[sig]=handler;
    return old;
}

static void raise_signal(int pid, int sig){
    if(sig<0||sig>=NSIG)return;
    if(sig==SIGKILL){tasks[pid].state=TASK_DEAD;return;}
    if(sig==SIGSTOP){tasks[pid].state=TASK_BLOCKED;return;}
    if(signal_handlers[sig])signal_handlers[sig](sig);
}

/* ================================================================ PROCESS GROUPS */
#define MAX_PGID 16
typedef struct {
    int leader;        /* PID of group leader */
    int count;         /* Number of processes in group */
} process_group_t;

static process_group_t process_groups[MAX_PGID];
static int pgid_count=0;
static int current_pgid=1;

static int setpgid(int pid, int pgid){
    if(pgid<0||pgid>=MAX_PGID)return -1;
    if(pid==0)pid=current_task;
    tasks[pid].pgid=pgid;
    return 0;
}

static pid_t getpgid(pid_t pid){
    if(pid==0)return current_pgid;
    return tasks[pid].pgid;
}

static pid_t getsid(pid_t pid){
    if(pid==0)return 1;
    return tasks[pid].sid;
}

/* ================================================================ FORK */
static pid_t do_fork(void){
    /* Find free task slot */
    int new_pid=-1;
    for(int i=1;i<MAX_TASKS;i++){
        if(tasks[i].state==TASK_DEAD||tasks[i].state==0){
            new_pid=i;break;
        }
    }
    if(new_pid<0){uart_puts("fork: no free task slots\n");return -1;}
    
    task_t *parent=&tasks[current_task];
    task_t *child=&tasks[new_pid];
    
    /* Copy task struct */
    kmemcpy(child,parent,sizeof(task_t));
    child->id=new_pid;
    child->state=TASK_READY;
    child->ticks=0;
    child->sleep_until=0;
    child->parent_pid=current_task;
    
    /* Copy stack - allocate new */
    child->stack=kmalloc(TASK_STACK);
    if(!child->stack){child->state=TASK_DEAD;return -1;}
    kmemcpy(child->stack,parent->stack,TASK_STACK);
    *((volatile u64*)child->stack)=TASK_CANARY_FOOT;
    
    /* Setup return value for child: fork returns 0 in child */
    u64 *sp=(u64*)(child->stack+TASK_STACK);
    sp[-1]=0; /* x0 = 0 (fork returns 0 in child) */
    child->sp_save=(u64)(sp-1);
    
    /* Child inherits pgid */
    child->pgid=current_pgid;
    
    /* Add to parent's children list */
    parent->children[parent->child_count++]=new_pid;
    if(parent->child_count>=8)parent->child_count=7;
    
    uart_puts("[FORK] Created child PID ");put_dec((u64)new_pid);
    uart_puts(" from parent ");put_dec((u64)current_task);uart_puts("\n");
    
    return new_pid;
}

/* ================================================================ EXECVE */
static int do_execve(const char *filename, char *const argv[], char *const envp[]){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){
        /* Try absolute path */
        if(filename[0]=='/'){
            vfs_node_t *cur=vfs_root;char seg[64];int i=1;
            while(filename[i]){
                int j=0;
                while(filename[i]&&filename[i]!='/'&&j<63)seg[j++]=filename[i++];
                seg[j]=0;if(filename[i]=='/')i++;
                if(j==0)continue;
                vfs_node_t *n=vfs_find(cur,seg);
                if(!n)return -1;
                if(filename[i]==0&&n->type==VFS_TYPE_FILE){f=n;break;}
                cur=n;
            }
        }
    }
    if(!f||f->type!=VFS_TYPE_FILE){
        uart_puts("execve: ");uart_puts(filename);uart_puts(": not found\n");
        return -1;
    }
    
    /* Check if it's a script (starts with #!) */
    if(f->size>=2&&f->data[0]=='#'&&f->data[1]=='!'){
        uart_puts("[EXEC] Script interpreter not implemented\n");
        return -1;
    }
    
    /* Check if it's ELF */
    u8 *elf=f->data;
    if(f->size>=4&&elf[0]==0x7f&&elf[1]=='E'&&elf[2]=='L'&&elf[3]=='F'){
        /* Load ELF into user space */
        Elf64_Ehdr *hdr=(Elf64_Ehdr*)elf;
        if(hdr->class==2){ /* 64-bit */
            /* Map segments to user space */
            Elf64_Phdr *ph=(Elf64_Phdr*)(elf+hdr->phoff);
            for(int i=0;i<hdr->phnum;i++){
                if(ph[i].type!=PT_LOAD)continue;
                u8 *dst=(u8*)ph[i].vaddr;
                u8 *src=elf+ph[i].offset;
                kmemcpy(dst,src,(size_t)ph[i].filesz);
                if(ph[i].memsz>ph[i].filesz)
                    kmemset(dst+ph[i].filesz,0,(size_t)(ph[i].memsz-ph[i].filesz));
            }
            uart_puts("[EXEC] ELF loaded, entry=");put_hex64(hdr->entry);uart_puts("\n");
            tasks[current_task].user_entry=hdr->entry;
            /* Clear registers and jump to entry */
            return 0;
        }
    }
    
    uart_puts("execve: ");uart_puts(filename);uart_puts(": cannot execute\n");
    return -1;
}

/* ================================================================ WAIT */
static pid_t do_wait(int *status){
    pid_t child=-1;
    for(int i=1;i<MAX_TASKS;i++){
        if(tasks[i].parent_pid==current_task){
            if(tasks[i].state==TASK_DEAD){
                child=i;
                if(status)*status=0;
                tasks[i].state=0; /* Free slot */
                return child;
            }
            child=i; /* Has living child */
        }
    }
    if(child<0){/* errno=ECHILD */return -1;}
    /* Block until a child exits */
    while(1){
        for(int i=1;i<MAX_TASKS;i++){
            if(tasks[i].parent_pid==current_task&&tasks[i].state==TASK_DEAD){
                if(status)*status=0;
                tasks[i].state=0;
                return i;
            }
        }
        task_sleep(10);
    }
}

static pid_t do_waitpid(pid_t pid, int *status, int options){
    if(pid==-1)return do_wait(status);
    if(pid<0||pid>=MAX_TASKS)return -1;
    if(tasks[pid].parent_pid!=current_task)return -1;
    if(tasks[pid].state!=TASK_DEAD){
        if(!(options&1)){/* WNOHANG */return 0;}
        task_sleep(10);
        return 0;
    }
    if(status)*status=0;
    tasks[pid].state=0;
    return pid;
}

/* ================================================================ KILL */
static int do_kill(pid_t pid, int sig){
    if(pid<0||pid>=MAX_TASKS){/* errno=ESRCH */return -1;}
    if(sig<0||sig>=NSIG){/* errno=EINVAL */return -1;}
    raise_signal((int)pid,sig);
    return 0;
}

static int do_killpg(int pgid, int sig){
    if(pgid<=0)return -1;
    for(int i=1;i<MAX_TASKS;i++){
        if(tasks[i].pgid==pgid){
            raise_signal(i,sig);
        }
    }
    return 0;
}

/* ================================================================ NICE */
static int do_nice(int inc){
    task_prio_t old_prio=tasks[current_task].prio;
    int new_prio=(int)tasks[current_task].prio+inc;
    if(new_prio<0)new_prio=0;
    if(new_prio>3)new_prio=3;
    tasks[current_task].prio=(task_prio_t)new_prio;
    return new_prio-(int)old_prio;
}

/* ================================================================ PTRACE (basic) */
#define PTRACE_TRACEME     0
#define PTRACE_PEEKTEXT    1
#define PTRACE_PEEKDATA    2
#define PTRACE_PEEKUSER    3
#define PTRACE_POKETEXT    4
#define PTRACE_POKEDATA    5
#define PTRACE_POKEUSER    6
#define PTRACE_CONT        7
#define PTRACE_KILL        8
#define PTRACE_SINGLESTEP  9
#define PTRACE_GETREGS     10
#define PTRACE_SETREGS     11
#define PTRACE_ATTACH      16
#define PTRACE_DETACH      17

static int ptraced_by[MAX_TASKS];
static int ptrace_options[MAX_TASKS];

static long do_ptrace(int request, pid_t pid, void *addr, void *data){
    if(pid<0||pid>=MAX_TASKS)return -1;
    switch(request){
        case PTRACE_TRACEME:
            ptraced_by[current_task]=current_task;
            tasks[current_task].traced=1;
            return 0;
        case PTRACE_ATTACH:
            ptraced_by[pid]=current_task;
            tasks[pid].traced=1;
            tasks[pid].state=TASK_BLOCKED;
            return 0;
        case PTRACE_DETACH:
            ptraced_by[pid]=0;
            tasks[pid].traced=0;
            tasks[pid].state=TASK_READY;
            return 0;
        case PTRACE_KILL:
            tasks[pid].state=TASK_DEAD;
            return 0;
        case PTRACE_CONT:
            tasks[pid].state=TASK_READY;
            return 0;
        case PTRACE_PEEKTEXT:
        case PTRACE_PEEKDATA:
            if(addr)return *(u64*)addr;
            return 0;
        case PTRACE_POKETEXT:
        case PTRACE_POKEDATA:
            if(addr&&data){*(u64*)addr=*(u64*)data;return 0;}
            return -1;
        default:
            uart_puts("ptrace: unsupported request ");put_dec((u64)request);uart_puts("\n");
            return -1;
    }
}

/* ================================================================ /PROC STAT */
static void write_proc_stat(char *buf, size_t bufsize, int pid){
    if(pid<0||pid>=MAX_TASKS){buf[0]=0;return;}
    task_t *t=&tasks[pid];
    char tmp[256];
    kstrcpy(tmp,"");kitoa((u64)pid,tmp+kstrlen(tmp));kstrcat(tmp," ");
    kstrcat(tmp,"(sh) ");kstrcat(tmp,t->state==TASK_RUNNING?"R":"S");
    kstrcat(tmp," ");kitoa((u64)t->parent_pid,tmp+kstrlen(tmp));
    kstrcat(tmp," 0 0 0 0 0 0 0 ");
    kitoa((u64)t->ticks,tmp+kstrlen(tmp));
    kstrcat(tmp," 0 0 0 0 0 0 0 0 0 ");
    kitoa((u64)t->prio,tmp+kstrlen(tmp));
    kstrcat(tmp," 0 0 0 0 0 0 0 0 0 0 0 0 0\n");
    kstrncpy(buf,tmp,bufsize-1);
}

/* ================================================================ TASK STRUCT EXTENSIONS */
static void init_process_subsystem(void){
    /* Initialize signal handlers to defaults */
    for(int i=0;i<NSIG;i++)signal_handlers[i]=default_signal_handler;
    /* Signal 9 (SIGKILL) and 19 (SIGSTOP) cannot be caught */
    signal_handlers[SIGKILL]=0;
    signal_handlers[SIGSTOP]=0;
    /* SIGCHLD is ignored by default */
    signal_handlers[SIGCHLD]=0;
    /* Initialize process groups */
    process_groups[0].leader=0;
    process_groups[0].count=1;
    pgid_count=1;
}
"""

# Add to exports
__all__ = ["MINIOS_PROCESS_C"]
