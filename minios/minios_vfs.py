# MiniOS Enhanced VFS - devfs, procfs, sysfs, mount points

MINIOS_VFS_C = r"""
/* ================================================================
 * MiniOS Enhanced VFS - Virtual File System with Mount Points
 * ================================================================
 * Features:
 * - devfs: /dev/null, /dev/zero, /dev/random, /dev/urandom, /dev/tty
 * - procfs: /proc/cpuinfo, /proc/meminfo, /proc/uptime, /proc/cmdline
 * - sysfs: /sys/class, /sys/devices, /sys/kernel
 * - Mount table: support for multiple filesystems
 * - File descriptors beyond VFS nodes
 * - Directory operations: opendir, readdir, closedir
 * ================================================================ */

/* ================================================================ FILE DESCRIPTORS */
#define MAX_FD 64
#define MAX_OPEN_FILES 32

typedef enum {
    FD_TYPE_VFS,      /* VFS node */
    FD_TYPE_DEV_NULL, /* /dev/null */
    FD_TYPE_DEV_ZERO, /* /dev/zero */
    FD_TYPE_DEV_RANDOM,/* /dev/urandom */
    FD_TYPE_DEV_TTY,  /* /dev/tty (UART) */
    FD_TYPE_PIPE,     /* Pipe */
    FD_TYPE_SOCKET    /* Network socket */
} fd_type_t;

typedef struct {
    int        used;
    fd_type_t  type;
    vfs_node_t *node;      /* For VFS type */
    size_t     offset;      /* Current position */
    int        flags;       /* O_RDONLY, O_WRONLY, O_RDWR */
    char       *pipe_buf;   /* For pipes */
    size_t     pipe_size;
    int        pipe_read_pos;
    int        pipe_write_pos;
} file_descriptor_t;

static file_descriptor_t fd_table[MAX_FD];
static spinlock_t fd_lock = 0;

/* File flags */
#define O_RDONLY 0
#define O_WRONLY 1
#define O_RDWR   2
#define O_APPEND 8
#define O_CREAT  16

static void fd_init(void){
    kmemset(fd_table, 0, sizeof(fd_table));
    /* Pre-open stdin, stdout, stderr */
    fd_table[0].used=1; fd_table[0].type=FD_TYPE_DEV_TTY; fd_table[0].flags=O_RDONLY;
    fd_table[1].used=1; fd_table[1].type=FD_TYPE_DEV_TTY; fd_table[1].flags=O_WRONLY;
    fd_table[2].used=1; fd_table[2].type=FD_TYPE_DEV_TTY; fd_table[2].flags=O_WRONLY;
}

static int fd_alloc(void){
    for(int i=3;i<MAX_FD;i++)if(!fd_table[i].used){fd_table[i].used=1;return i;}
    return -1;
}

static void fd_free(int fd){
    if(fd>=3&&fd<MAX_FD)fd_table[fd].used=0;
}

static file_descriptor_t *fd_get(int fd){
    if(fd<0||fd>=MAX_FD||!fd_table[fd].used)return 0;
    return &fd_table[fd];
}

static int fd_read(int fd, void *buf, size_t len){
    file_descriptor_t *f=fd_get(fd);
    if(!f)return -1;
    switch(f->type){
        case FD_TYPE_DEV_TTY:{
            char *dst=(char*)buf;
            for(size_t i=0;i<len;i++){
                while(!uart_getc_nb(dst+i));
            }
            return len;
        }
        case FD_TYPE_DEV_ZERO:{
            kmemset(buf, 0, len);
            return len;
        }
        case FD_TYPE_DEV_NULL: return 0;
        case FD_TYPE_DEV_RANDOM:{
            /* Pseudo-random from timer */
            char *dst=(char*)buf;
            for(size_t i=0;i<len;i++)dst[i]=(char)(tick_count*17+i*31)&0xFF;
            return len;
        }
        case FD_TYPE_VFS:{
            if(!f->node||f->node->type!=VFS_TYPE_FILE)return -1;
            size_t avail=f->node->size-f->offset;
            size_t to_read=len<avail?len:avail;
            kmemcpy(buf, f->node->data+f->offset, to_read);
            f->offset+=to_read;
            return to_read;
        }
        case FD_TYPE_PIPE:{
            size_t avail=f->pipe_size-f->pipe_read_pos;
            size_t to_read=len<avail?len:avail;
            kmemcpy(buf, f->pipe_buf+f->pipe_read_pos, to_read);
            f->pipe_read_pos+=to_read;
            return to_read;
        }
        default: return -1;
    }
}

static int fd_write(int fd, const void *buf, size_t len){
    file_descriptor_t *f=fd_get(fd);
    if(!f)return -1;
    switch(f->type){
        case FD_TYPE_DEV_TTY:{
            const char *src=(const char*)buf;
            for(size_t i=0;i<len;i++)uart_putc(src[i]);
            return len;
        }
        case FD_TYPE_DEV_NULL:
        case FD_TYPE_DEV_ZERO: return len;
        case FD_TYPE_VFS:{
            if(!f->node||f->node->type!=VFS_TYPE_FILE)return -1;
            /* Expand node data if needed */
            size_t new_size=f->offset+len;
            if(new_size>f->node->size){
                void *new_data=kmalloc(new_size);
                if(f->node->data){kmemcpy(new_data,f->node->data,f->node->size);}
                kmemset(new_data+f->node->size, 0, new_size-f->node->size);
                f->node->data=(u8*)new_data;
            }
            kmemcpy(f->node->data+f->offset, buf, len);
            f->node->size=new_size;
            f->offset+=len;
            return len;
        }
        case FD_TYPE_PIPE:{
            size_t avail=256-f->pipe_write_pos;
            size_t to_write=len<avail?len:avail;
            kmemcpy(f->pipe_buf+f->pipe_write_pos, buf, to_write);
            f->pipe_write_pos+=to_write;
            f->pipe_size+=to_write;
            return to_write;
        }
        default: return -1;
    }
}

/* ================================================================ PIPE CREATION */
static int pipe(int fds[2]){
    fds[0]=fd_alloc();fds[1]=fd_alloc();
    if(fds[0]<0||fds[1]<0)return -1;
    fd_table[fds[0]].type=FD_TYPE_PIPE;
    fd_table[fds[0]].pipe_buf=kmalloc(256);
    fd_table[fds[0]].pipe_size=0;
    fd_table[fds[1]].type=FD_TYPE_PIPE;
    fd_table[fds[1]].pipe_buf=fd_table[fds[0]].pipe_buf;
    fd_table[fds[1]].pipe_size=0;
    return 0;
}

/* ================================================================ MOUNT TABLE */
#define MAX_MOUNTS 8
typedef struct {
    const char *device;
    const char *mount_point;
    const char *fs_type;
    void *data;
    int mounted;
} mount_entry_t;

static mount_entry_t mount_table[MAX_MOUNTS];
static int mount_count=0;
static spinlock_t mount_lock=0;

static int do_mount(const char *device, const char *mount_point, const char *fs_type){
    if(mount_count>=MAX_MOUNTS)return -1;
    mount_table[mount_count].device=device;
    mount_table[mount_count].mount_point=mount_point;
    mount_table[mount_count].fs_type=fs_type;
    mount_table[mount_count].mounted=1;
    mount_count++;
    return 0;
}

static int do_umount(const char *mount_point){
    for(int i=0;i<mount_count;i++){
        if(kstrcmp(mount_table[i].mount_point,mount_point)==0){
            mount_table[i].mounted=0;
            return 0;
        }
    }
    return -1;
}

static void show_mounts(void){
    uart_puts("Filesystem     1K-blocks      Used Available Use% Mounted on\n");
    for(int i=0;i<mount_count;i++){
        if(mount_table[i].mounted){
            uart_puts(mount_table[i].fs_type);
            uart_puts("              65536       128     65408   1% ");
            uart_puts(mount_table[i].mount_point);
            uart_puts("\n");
        }
    }
    /* Always show ramfs */
    uart_puts("ramfs              65536       128     65408   1% /\n");
}

/* ================================================================ DEVFS - Device Filesystem */
static void devfs_init(void){
    /* /dev/null */
    vfs_node_t *dev=vfs_find(vfs_root,"dev");
    if(!dev){dev=vfs_mknode(vfs_root,"dev",VFS_TYPE_DIR);dev->mode=0755;}
    vfs_node_t *null=vfs_mknode(dev,"null",VFS_TYPE_FILE);
    if(null){null->mode=0666;null->size=0;null->data=0;}
    vfs_node_t *zero=vfs_mknode(dev,"zero",VFS_TYPE_FILE);
    if(zero){zero->mode=0666;zero->size=0;zero->data=0;}
    vfs_node_t *urandom=vfs_mknode(dev,"urandom",VFS_TYPE_FILE);
    if(urandom){urandom->mode=0444;urandom->size=0;urandom->data=0;}
    vfs_node_t *random=vfs_mknode(dev,"random",VFS_TYPE_FILE);
    if(random){random->mode=0444;random->size=0;random->data=0;}
    vfs_node_t *tty=vfs_mknode(dev,"tty",VFS_TYPE_FILE);
    if(tty){tty->mode=0666;tty->size=0;tty->data=0;}
    vfs_node_t *console=vfs_mknode(dev,"console",VFS_TYPE_FILE);
    if(console){console->mode=0600;console->size=0;console->data=0;}
}

/* ================================================================ PROCFS - Process Information */
static void procfs_init(void){
    vfs_node_t *proc=vfs_find(vfs_root,"proc");
    if(!proc)proc=vfs_mknode(vfs_root,"proc",VFS_TYPE_DIR);
    proc->mode=0555;
}

/* Dynamic procfs entries - regenerated on access */
static const char *procfs_cpuinfo_content=
"processor       : 0\n"
"model name     : ARM Cortex-A53\n"
"cpu implementer : 0x41\n"
"cpu architecture: 8\n"
"cpu variant    : 0x0\n"
"cpu part       : 0xd03\n"
"cpu revision   : 4\n\n"
"Features        : fp asimd evtstrm crc32 cpuid\n"
"CPU implementer : 0x41\n"
"CPU architecture: 8\n"
"CPU variant     : 0x0\n"
"CPU part        : 0xd03\n"
"CPU revision    : 4\n";

static const char *procfs_meminfo_content=
"MemTotal:       524288 kB\n"
"MemFree:        458752 kB\n"
"MemAvailable:   458752 kB\n"
"Buffers:            0 kB\n"
"Cached:             0 kB\n"
"SwapCached:         0 kB\n"
"Active:             0 kB\n"
"Inactive:           0 kB\n"
"Active(anon):       0 kB\n"
"Inactive(anon):     0 kB\n"
"Active(file):       0 kB\n"
"Inactive(file):     0 kB\n"
"Unreclaimable:      0 kB\n"
"VmallocTotal:   1048576 kB\n"
"VmallocUsed:        0 kB\n"
"VmallocChunk:       0 kB\n";

static void procfs_update(void){
    vfs_node_t *proc=vfs_find(vfs_root,"proc");
    if(!proc)return;
    /* Update meminfo */
    char meminfo[512];
    kstrcpy(meminfo,"MemTotal:       524288 kB\n");
    kstrcat(meminfo,"MemFree:        ");
    char free_kb[16];kitoa((heap_ptr-HEAP_START)/1024,free_kb);kstrcat(meminfo,free_kb);
    kstrcat(meminfo," kB\n");
    vfs_node_t *mi=vfs_find(proc,"meminfo");
    if(mi&&mi->data)kfree(mi->data);
    mi->data=kmalloc(kstrlen(meminfo)+1);
    if(mi->data){kmemcpy(mi->data,meminfo,kstrlen(meminfo)+1);mi->size=kstrlen(meminfo);}
    /* Update uptime */
    char uptime[64];
    kstrcpy(uptime,"");kitoa(tick_count/100,uptime);kstrcat(uptime,".0 ");
    kitoa(tick_count/100,uptime+kstrlen(uptime));kstrcat(uptime,"\n");
    vfs_node_t *up=vfs_find(proc,"uptime");
    if(up&&up->data)kfree(up->data);
    up->data=kmalloc(kstrlen(uptime)+1);
    if(up->data){kmemcpy(up->data,uptime,kstrlen(uptime)+1);up->size=kstrlen(uptime);}
}

static void procfs_create_entries(void){
    vfs_node_t *proc=vfs_find(vfs_root,"proc");
    if(!proc)return;
    /* /proc/version */
    vfs_node_t *ver=vfs_mknode(proc,"version",VFS_TYPE_FILE);
    if(ver){ver->mode=0444;const char *vs="MiniOS 3.0.0-aarch64\n";ver->data=(u8*)vs;ver->size=kstrlen(vs);}
    /* /proc/cpuinfo */
    vfs_node_t *cpu=vfs_mknode(proc,"cpuinfo",VFS_TYPE_FILE);
    if(cpu){cpu->mode=0444;cpu->data=(u8*)procfs_cpuinfo_content;cpu->size=kstrlen(procfs_cpuinfo_content);}
    /* /proc/meminfo */
    vfs_node_t *mem=vfs_mknode(proc,"meminfo",VFS_TYPE_FILE);
    if(mem){mem->mode=0444;mem->data=kmalloc(512);kmemset(mem->data,0,512);mem->size=0;}
    /* /proc/uptime */
    vfs_node_t *up=vfs_mknode(proc,"uptime",VFS_TYPE_FILE);
    if(up){up->mode=0444;up->data=kmalloc(64);kmemset(up->data,0,64);up->size=0;}
    /* /proc/cmdline */
    vfs_node_t *cmd=vfs_mknode(proc,"cmdline",VFS_TYPE_FILE);
    if(cmd){cmd->mode=0444;const char *c="root=/dev/ram0 console=ttyAMA0";cmd->data=(u8*)c;cmd->size=kstrlen(c);}
    /* /proc/self/ */
    vfs_node_t *self=vfs_mknode(proc,"self",VFS_TYPE_DIR);
    if(self){self->mode=0555;}
    /* /proc/PID/ entries - simplified */
    char pid_str[16];kitoa((u64)current_task,pid_str);
    vfs_node_t *pid_dir=vfs_mknode(self,pid_str,VFS_TYPE_DIR);
    if(pid_dir){
        vfs_node_t *status=vfs_mknode(pid_dir,"status",VFS_TYPE_FILE);
        if(status){status->mode=0444;const char *s="Name:   shell\nState:  Running\n";status->data=(u8*)s;status->size=kstrlen(s);}
        vfs_node_t *cmdline=vfs_mknode(pid_dir,"cmdline",VFS_TYPE_FILE);
        if(cmdline){cmdline->mode=0444;const char *c="/bin/sh\n";cmdline->data=(u8*)c;cmdline->size=kstrlen(c);}
    }
}

/* ================================================================ SYSFS - System Information */
static void sysfs_init(void){
    vfs_node_t *sys=vfs_find(vfs_root,"sys");
    if(!sys)sys=vfs_mknode(vfs_root,"sys",VFS_TYPE_DIR);
    sys->mode=0555;
    /* /sys/class */
    vfs_node_t *cls=vfs_mknode(sys,"class",VFS_TYPE_DIR);
    if(cls){
        vfs_node_t *net=vfs_mknode(cls,"net",VFS_TYPE_DIR);
        vfs_node_t *tty=vfs_mknode(cls,"tty",VFS_TYPE_DIR);
        vfs_node_t *block=vfs_mknode(cls,"block",VFS_TYPE_DIR);
    }
    /* /sys/devices */
    vfs_node_t *devs=vfs_mknode(sys,"devices",VFS_TYPE_DIR);
    if(devs){
        vfs_node_t *platform=vfs_mknode(devs,"platform",VFS_TYPE_DIR);
        if(platform){
            vfs_node_t *serial=vfs_mknode(platform,"serial",VFS_TYPE_DIR);
        }
    }
    /* /sys/kernel */
    vfs_node_t *kernel=vfs_mknode(sys,"kernel",VFS_TYPE_DIR);
    if(kernel){
        vfs_node_t *kmem=vfs_mknode(kernel,"kmem",VFS_TYPE_FILE);
        if(kmem){kmem->mode=0644;}
        vfs_node_t *version=vfs_mknode(kernel,"version",VFS_TYPE_FILE);
        if(version){const char *v="MiniOS 3.0.0 #1 SMP\n";version->data=(u8*)v;version->size=kstrlen(v);}
        vfs_node_t *mm=vfs_mknode(kernel,"mm",VFS_TYPE_FILE);
    }
}

/* ================================================================ DIRECTORY ITERATION (POSIX-like) */
typedef struct {
    vfs_node_t *dir;
    vfs_node_t *current;
} DIR;

static DIR *opendir(const char *path){
    vfs_node_t *n=vfs_find(vfs_cwd,path);
    if(!n||n->type!=VFS_TYPE_DIR)return 0;
    DIR *d=kmalloc(sizeof(DIR));
    if(!d)return 0;
    d->dir=n;d->current=n->child;
    return d;
}

static struct dirent {
    char d_name[256];
    int d_type;
} *readdir(DIR *d){
    if(!d||!d->current)return 0;
    static struct dirent entry;
    kstrncpy(entry.d_name,d->current->name,255);
    entry.d_type=d->current->type;
    d->current=d->current->next;
    return &entry;
}

static void closedir(DIR *d){
    if(d)kfree(d);
}

/* ================================================================ REALPATH */
static void realpath(const char *path, char *buf){
    if(path[0]=='/'){
        kstrncpy(buf,path,255);
    } else {
        shell_pwd_str(buf,255);
        if(buf[kstrlen(buf)-1]!='/')kstrcat(buf,"/");
        kstrcat(buf,path);
    }
}

/* ================================================================ STAT FSTRUCT */
typedef struct {
    u64 st_dev;
    u64 st_ino;
    u32 st_mode;
    u32 st_nlink;
    u32 st_uid;
    u32 st_gid;
    u64 st_size;
    u64 st_atime;
    u64 st_mtime;
    u64 st_ctime;
} stat_t;

static int do_stat(const char *path, stat_t *st){
    vfs_node_t *n=vfs_find(vfs_cwd,path);
    if(!n){
        /* Try absolute path */
        if(path[0]=='/'){
            vfs_node_t *cur=vfs_root;
            char seg[64];int i=1;
            while(path[i]){
                int j=0;
                while(path[i]&&path[i]!='/'&&j<63)seg[j++]=path[i++];
                seg[j]=0;if(path[i]=='/')i++;
                if(j==0)continue;
                n=vfs_find(cur,seg);
                if(!n)return -1;
                cur=n;
            }
        }
    }
    if(!n)return -1;
    st->st_dev=0;st->st_ino=(u64)n;
    st->st_mode=n->mode;
    st->st_nlink=1;st->st_uid=0;st->st_gid=0;
    st->st_size=n->size;
    st->st_atime=tick_count;st->st_mtime=tick_count;st->st_ctime=tick_count;
    return 0;
}

/* ================================================================ EXTENDED VFS OPERATIONS */
static int vfs_link(const char *oldpath, const char *newpath){
    vfs_node_t *old=vfs_find(vfs_cwd,oldpath);
    if(!old){uart_puts("link: oldpath not found\n");return -1;}
    vfs_node_t *new=vfs_mknode(vfs_cwd,newpath,VFS_TYPE_FILE);
    if(!new){uart_puts("link: failed\n");return -1;}
    new->data=old->data;new->size=old->size;
    new->mode=old->mode;
    return 0;
}

static int vfs_symlink(const char *target, const char *linkpath){
    vfs_node_t *link=vfs_mknode(vfs_cwd,linkpath,VFS_TYPE_LINK);
    if(!link){uart_puts("symlink: failed\n");return -1;}
    link->data=(u8*)target;link->size=kstrlen(target);
    return 0;
}

static int vfs_readlink(const char *path, char *buf, size_t bufsize){
    vfs_node_t *n=vfs_find(vfs_cwd,path);
    if(!n||n->type!=VFS_TYPE_LINK){uart_puts("readlink: not a symlink\n");return -1;}
    size_t len=n->size<bufsize-1?n->size:bufsize-1;
    kmemcpy(buf,n->data,len);buf[len]=0;
    return len;
}

static int vfs_truncate(const char *path, size_t len){
    vfs_node_t *n=vfs_find(vfs_cwd,path);
    if(!n||n->type!=VFS_TYPE_FILE){uart_puts("truncate: not a file\n");return -1;}
    if(len==0){n->size=0;return 0;}
    void *new_data=kmalloc(len);
    if(!new_data)return -1;
    size_t copy=len<n->size?len:n->size;
    if(n->data){kmemcpy(new_data,n->data,copy);kfree(n->data);}
    n->data=(u8*)new_data;
    n->size=len;
    return 0;
}

/* ================================================================ FILE LOCKING */
typedef struct {int locked;int pid;} file_lock_t;
static file_lock_t file_locks[MAX_OPEN_FILES];

static int flock(int fd, int operation){
    file_descriptor_t *f=fd_get(fd);
    if(!f)return -1;
    int idx=fd-3;
    if(idx<0||idx>=MAX_OPEN_FILES)return -1;
    if(operation&0x01){/* LOCK_EX or LOCK_SH */
        if(file_locks[idx].locked)return -1;
        file_locks[idx].locked=1;
        file_locks[idx].pid=current_task;
    }
    if(operation&0x08){/* LOCK_UN */
        file_locks[idx].locked=0;
    }
    return 0;
}

/* ================================================================ CHOWN / CHGRP (stub) */
static int do_chown(const char *path, int uid, int gid){
    vfs_node_t *n=vfs_find(vfs_cwd,path);
    if(!n)return -1;
    n->uid=uid;n->gid=gid;
    return 0;
}

/* ================================================================ UMASK */
static int current_umask=0022;
static int umask(int mask){int old=current_umask;current_umask=mask;return old;}
"""

# Add to exports
__all__ = ["MINIOS_VFS_C"]
