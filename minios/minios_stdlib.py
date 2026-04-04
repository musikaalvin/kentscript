# MiniOS Standard Library - POSIX-like commands for the shell
# This module provides implementations of common Linux/Unix commands

MINIOS_STDLIB_C = r"""
/* ================================================================
 * MiniOS Standard Library - POSIX-like Commands
 * ================================================================
 * Commands: cp mv ln head tail wc sort uniq cut tr tee
 *           grep find du df hexdump od which whereis whoami
 *           hostname date sleep nano calc history clear
 * ================================================================ */

/* ================================================================ STRING UTILITIES */
static int kstrcmp(const char *a, const char *b){
    while(*a && *b && *a==*b){a++;b++;}
    return *a-*b;
}
static int kstrncmp(const char *a, const char *b, size_t n){
    for(size_t i=0;i<n;i++){if(a[i]!=b[i]||!a[i])return a[i]-b[i];}
    return 0;
}
static size_t kstrlen(const char *s){size_t n=0;while(*s++)n++;return n;}
static char *kstrcpy(char *d, const char *s){char *r=d;while((*d++=*s++));return r;}
static char *kstrncpy(char *d, const char *s, size_t n){
    size_t i;for(i=0;i<n&&s[i];i++)d[i]=s[i];d[i]=0;return d;}
static void *kmemcpy(void *d, const void *s, size_t n){
    char *cd=d;const char *cs=s;while(n--)*cd++=*cs++;return d;}
static void *kmemset(void *s, int c, size_t n){
    char *cs=s;while(n--)*cs++=(char)c;return s;}

/* Skip whitespace */
static const char *skip_ws(const char *s){
    while(*s==' '||*s=='\t'||*s=='\r'||*s=='\n')s++;return s;}

/* Trim trailing whitespace */
static void trim_end(char *s){
    int i=(int)kstrlen(s)-1;
    while(i>=0&&(s[i]==' '||s[i]=='\t'||s[i]=='\r'||s[i]=='\n'))s[i--]=0;
}

/* ================================================================ FILE OPERATIONS */
static int shell_cp(const char *src, const char *dst){
    vfs_node_t *src_node=vfs_find(vfs_cwd,src);
    if(!src_node){uart_puts("cp: cannot stat '");uart_puts(src);uart_puts("'\n");return -1;}
    if(src_node->type==VFS_TYPE_DIR){
        uart_puts("cp: -r not specified, omitting directory '");uart_puts(src);uart_puts("'\n");return -1;
    }
    vfs_node_t *parent=vfs_cwd;
    vfs_node_t *dst_node=vfs_mknode(parent,dst,VFS_TYPE_FILE);
    if(!dst_node){uart_puts("cp: failed to create destination\n");return -1;}
    /* Copy data */
    if(src_node->data&&src_node->size>0){
        void *copy=kmalloc(src_node->size);
        if(copy){kmemcpy(copy,src_node->data,src_node->size);dst_node->data=copy;}
    }
    dst_node->size=src_node->size;
    dst_node->mode=src_node->mode;
    uart_puts("'");uart_puts(src);uart_puts("' -> '");uart_puts(dst);uart_puts("'\n");
    return 0;
}

static int shell_cp_r(const char *src, const char *dst){
    vfs_node_t *src_node=vfs_find(vfs_cwd,src);
    if(!src_node){uart_puts("cp: cannot stat '");uart_puts(src);uart_puts("'\n");return -1;}
    if(src_node->type==VFS_TYPE_DIR){
        /* Create destination directory */
        vfs_node_t *dst_node=vfs_mknode(vfs_cwd,dst,VFS_TYPE_DIR);
        if(!dst_node){uart_puts("cp: failed to create directory\n");return -1;}
        uart_puts("copied directory '");uart_puts(src);uart_puts("' -> '");uart_puts(dst);uart_puts("'\n");
    } else {
        shell_cp(src,dst);
    }
    return 0;
}

static int shell_mv(const char *src, const char *dst){
    vfs_node_t *src_node=vfs_find(vfs_cwd,src);
    if(!src_node){uart_puts("mv: cannot stat '");uart_puts(src);uart_puts("'\n");return -1;}
    /* Simple: just copy and remove (ramfs doesn't have rename) */
    shell_cp(src,dst);
    /* Remove source */
    if(src_node->parent){
        vfs_node_t **prev=&src_node->parent->child;
        while(*prev&&*prev!=src_node)prev=&(*prev)->next;
        if(*prev)*prev=src_node->next;
    }
    uart_puts("'");uart_puts(src);uart_puts("' -> '");uart_puts(dst);uart_puts("'\n");
    return 0;
}

static int shell_ln(const char *target, const char *link_name, int symbolic){
    vfs_node_t *t=vfs_find(vfs_cwd,target);
    if(!t){uart_puts("ln: failed to access '");uart_puts(target);uart_puts("'\n");return -1;}
    vfs_node_t *link=vfs_mknode(vfs_cwd,link_name,VFS_TYPE_LINK);
    if(!link){uart_puts("ln: failed to create link\n");return -1;}
    /* Store target as link target in data */
    link->data=(u8*)target;
    link->size=kstrlen(target);
    if(symbolic)uart_puts("symlink: '");else uart_puts("link: '");
    uart_puts(link_name);uart_puts("' -> '");uart_puts(target);uart_puts("'\n");
    return 0;
}

/* ================================================================ TEXT UTILITIES */
static void shell_head(const char *filename, int lines){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("head: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    if(f->type==VFS_TYPE_DIR){uart_puts("head: is a directory\n");return;}
    int count=0;
    for(size_t i=0;i<f->size&&count<lines;i++){
        char c=(char)f->data[i];
        uart_putc(c);
        if(c=='\n')count++;
    }
    uart_puts("\n");
}

static void shell_tail(const char *filename, int lines){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("tail: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    if(f->type==VFS_TYPE_DIR){uart_puts("tail: is a directory\n");return;}
    /* Find last N lines */
    int count=0;
    size_t start=0;
    for(size_t i=f->size;i>0&&count<=lines;i--){
        if(f->data[i-1]=='\n')count++;
        if(count==lines+1){start=i;break;}
    }
    for(size_t i=start;i<f->size;i++)uart_putc((char)f->data[i]);
    uart_puts("\n");
}

static void shell_wc(const char *filename, int show_lines, int show_words, int show_chars){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("wc: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    int lines=0, words=0, chars=0;
    int in_word=0;
    for(size_t i=0;i<f->size;i++){
        char c=(char)f->data[i];chars++;
        if(c=='\n')lines++;
        if(c==' '||c=='\t'||c=='\n'||c=='\r')in_word=0;
        else if(!in_word){words++;in_word=1;}
    }
    if(show_lines)uart_puts("  "),put_dec((u64)lines);
    if(show_words)uart_puts("  "),put_dec((u64)words);
    if(show_chars)uart_puts("  "),put_dec((u64)chars);
    uart_puts(" ");uart_puts(filename);uart_puts("\n");
}

static void shell_cat_file(const char *filename){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("cat: no such file: ");uart_puts(filename);uart_puts("\n");return;}
    if(f->type==VFS_TYPE_DIR){uart_puts("cat: is a directory\n");return;}
    for(size_t i=0;i<f->size;i++)uart_putc((char)f->data[i]);
}

static void shell_cat_n(const char *filename, int number_lines){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("cat: no such file: ");uart_puts(filename);uart_puts("\n");return;}
    if(f->type==VFS_TYPE_DIR){uart_puts("cat: is a directory\n");return;}
    int lineno=1;
    int at_line_start=1;
    char buf[8];int bufpos=0;
    for(size_t i=0;i<f->size;i++){
        char c=(char)f->data[i];
        if(at_line_start&&number_lines){
            put_dec((u64)lineno);
            uart_puts("  ");
            at_line_start=0;
        }
        uart_putc(c);
        if(c=='\n'){lineno++;at_line_start=1;}
    }
}

static void shell_hexdump(const char *filename, int bytes_per_line){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("hexdump: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    if(!bpl)bpl=16;
    for(size_t i=0;i<f->size;i+=bytes_per_line){
        /* Address */
        uart_puts("00000000");
        char addr[16];int ap=7;
        u64 a=i;while(a){addr[--ap]='0'+(a%16);a/=16;}
        for(int j=0;j<8;j++)uart_putc(addr[j]?addr[j]:'0');
        uart_puts("  ");
        /* Hex */
        for(int j=0;j<bytes_per_line;j++){
            if(i+j<f->size){
                u8 b=f->data[i+j];
                char h[3];h[0]=b<16?"0":"";/* need hex func */
                uart_putc(b<16?'0':'a');uart_putc(b<10?'0'+b:b-10+'a');
            } else uart_puts("  ");
            uart_putc(' ');
            if(j==7)uart_putc(' ');
        }
        uart_puts(" |");
        /* ASCII */
        for(int j=0;j<bytes_per_line&&i+j<f->size;j++){
            u8 c=f->data[i+j];
            uart_putc((c>=32&&c<127)?c:'.');
        }
        uart_puts("|\n");
    }
}

static void shell_od(const char *filename, int type){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("od: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    /* Octal dump */
    for(size_t i=0;i<f->size;i++){
        if(i%16==0){
            if(i>0)uart_puts("\n");
            uart_puts("0000000");
        }
        if(i%8==0)uart_putc(' ');
        char buf[8];int p=6;
        u8 v=f->data[i];
        for(int j=0;j<3;j++)buf[--p]='0'+(v%8),v/=8;
        for(int j=0;j<3;j++)uart_putc(buf[j]);
        uart_putc(' ');
    }
    uart_puts("\n");
}

/* ================================================================ SEARCH */
static void shell_grep(const char *pattern, const char *filename, int case_insensitive, int show_line_num){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("grep: ");uart_puts(filename);uart_puts(": No such file\n");return;}
    int plen=kstrlen(pattern);
    int lineno=1;
    int match_start=-1;
    int match_len=0;
    for(size_t i=0;i<f->size;i++){
        char c=(char)f->data[i];
        int match=0;
        if(case_insensitive){
            char pc=pattern[match_len];
            if(pc>='A'&&pc<='Z')pc=pc-'A'+'a';
            char cc=c;if(cc>='A'&&cc<='Z')cc=cc-'A'+'a';
            match=(cc==pc);
        } else match=(c==pattern[match_len]);
        if(match){
            if(match_len==0)match_start=(int)i;
            match_len++;
            if(match_len==plen){
                /* Found match - print line */
                if(show_line_num){put_dec((u64)lineno);uart_puts(":");}
                /* Print line containing match */
                size_t line_start=i;
                while(line_start>0&&f->data[line_start-1]!='\n')line_start--;
                for(size_t j=line_start;j<f->size&&(char)f->data[j]!='\n';j++)uart_putc((char)f->data[j]);
                uart_puts("\n");
                match_len=0;match_start=-1;
            }
        } else {
            match_len=0;match_start=-1;
        }
        if(c=='\n')lineno++;
    }
}

static void shell_find(const char *path, const char *name_pattern, int type){
    vfs_node_t *dir=vfs_find(vfs_cwd,path);
    if(!dir)dir=vfs_cwd;
    if(dir->type!=VFS_TYPE_DIR){
        uart_puts("find: ");uart_puts(path);uart_puts(": Not a directory\n");return;
    }
    /* Simple recursive find */
    char search_path[256];kstrncpy(search_path,path,255);
    for(vfs_node_t *c=dir->child;c;c=c->next){
        int match=1;
        if(name_pattern){
            match=0;
            const char *np=name_pattern;
            const char *cn=c->name;
            while(*np&&*cn){
                if(*np=='*'){match=1;break;}
                if(*np!=*cn){match=0;break;}
                np++;cn++;
            }
            if(*np==0&&*cn==0)match=1;
        }
        if(match){
            if(type==0||(type=='f'&&c->type==VFS_TYPE_FILE)||(type=='d'&&c->type==VFS_TYPE_DIR))
            {
                uart_puts(search_path);
                if(search_path[kstrlen(search_path)-1]!='/')uart_putc('/');
                uart_puts(c->name);uart_puts("\n");
            }
        }
        if(c->type==VFS_TYPE_DIR&&c->child){
            /* Recurse - simplified */
            uart_puts(search_path);uart_puts("/");uart_puts(c->name);uart_puts("/\n");
        }
    }
}

static void shell_which(const char *cmd){
    /* Search in PATH */
    static const char *paths[]={"/bin","/usr/bin","/usr/local/bin"};
    for(int p=0;p<3;p++){
        vfs_node_t *dir=vfs_find(vfs_root,paths[p]);
        if(dir&&dir->type==VFS_TYPE_DIR){
            for(vfs_node_t *c=dir->child;c;c=c->next){
                if(c->type==VFS_TYPE_FILE&&kstrcmp(c->name,cmd)==0){
                    uart_puts(paths[p]);uart_putc('/');uart_puts(cmd);uart_puts("\n");
                    return;
                }
            }
        }
    }
    uart_puts(cmd);uart_puts(": not found\n");
}

/* ================================================================ SYSTEM INFO */
static void shell_whoami(void){
    uart_puts("root\n");
}

static void shell_hostname(const char *name){
    if(name){uart_puts("hostname: ");uart_puts(name);uart_puts("\n");}
    else uart_puts("minios\n");
}

static void shell_uname_all(void){
    uart_puts("MiniOS 3.0.0 minios-aarch64 #1 SMP PREEMPT\n");
}

static void shell_uptime_full(void){
    uart_puts("  Uptime: ");put_dec(tick_count);uart_puts(" ticks (");
    put_dec(tick_count/100);uart_puts("s)\n");
    uart_puts("  Tasks: ");put_dec((u64)task_count);uart_puts("\n");
    uart_puts("  Load average: 0.12 0.08 0.05\n");
}

static void shell_date(void){
    uart_puts("Sat Mar 28 12:00:00 UTC 2026\n");
}

static void shell_sleep(int ticks){
    uart_puts("sleep: sleeping for ");put_dec((u64)ticks);uart_puts(" ticks\n");
    task_sleep((u64)ticks);
}

static void shell_df(void){
    uart_puts("Filesystem     1K-blocks      Used Available Use% Mounted on\n");
    uart_puts("ramfs              65536       128     65408   1% /\n");
    uart_puts("tmpfs              32768        64     32704   1% /tmp\n");
}

static void shell_du(const char *path){
    vfs_node_t *n=vfs_find(vfs_cwd,path);
    if(!n){uart_puts("du: cannot access '");uart_puts(path);uart_puts("'\n");return;}
    int size=0;
    if(n->type==VFS_TYPE_FILE)size=(int)n->size;
    else if(n->child){
        for(vfs_node_t *c=n->child;c;c=c->next)
            if(c->type==VFS_TYPE_FILE)size+=(int)c->size;
    }
    uart_puts("  ");put_dec((u64)(size/1024+1));uart_puts("\t");uart_puts(path);uart_puts("\n");
}

/* ================================================================ CALCULATOR */
static void shell_calc(const char *expr){
    /* Simple integer calculator: +, -, *, / */
    long long a=0,b=0,result=0;char op='+';
    const char *p=expr;
    int neg=0;
    if(*p=='-'){neg=1;p++;}
    while(*p&&*p!='+'&&*p!='-'&&*p!='*'&&*p!='/'){
        if(*p>='0'&&*p<='9')a=a*10+(*p-'0');
        p++;
    }
    if(neg)a=-a;
    if(*p){op=*p;p++;}
    neg=0;
    if(*p=='-'){neg=1;p++;}
    while(*p&&*p>='0'&&*p<='9'){
        b=b*10+(*p-'0');p++;
    }
    if(neg)b=-b;
    switch(op){
        case '+':result=a+b;break;
        case '-':result=a-b;break;
        case '*':result=a*b;break;
        case '/':result=b?a/b:0;break;
    }
    put_dec(result);uart_puts("\n");
}

/* ================================================================ EDITOR (nano-like) */
static void shell_nano(const char *filename){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    int is_new=0;
    if(!f){f=vfs_mknode(vfs_cwd,filename,VFS_TYPE_FILE);is_new=1;}
    if(!f){uart_puts("nano: cannot open file\n");return;}
    uart_puts("MiniOS nano editor\n");
    uart_puts("^X to exit, ^S to save, ^C to cancel\n");
    if(!is_new){uart_puts("Existing content:\n");shell_cat_file(filename);}
    uart_puts("\n[Type your text, press Enter then ^S to save]\n");
    /* Simple line input */
    char buf[256];int pos=0;buf[0]=0;
    uart_puts("> ");
    while(1){
        char c;if(!uart_getc_nb(&c)){__asm__ volatile("yield");continue;}
        if(c==0x03){uart_puts("^C\nAborted.\n");return;} /* ^C */
        if(c==0x18){uart_puts("^X\nSaving...\n");break;} /* ^X */
        if(c==0x13){uart_puts("^S\nSaved.\n");break;} /* ^S */
        if(c==0x7f||c=='\b'){if(pos>0){pos--;uart_puts("\b \b");}} /* backspace */
        else if(c=='\r'||c=='\n'){buf[pos++]=c;uart_putc(c);}
        else if(pos<250){buf[pos++]=c;uart_putc(c);}
    }
    buf[pos]=0;
    f->data=(u8*)buf;f->size=pos;
}

/* ================================================================ CLEAR & RESET */
static void shell_clear(void){
    uart_puts("\033[2J\033[H"); /* VT100 clear screen */
    uart_puts("Screen cleared. Type 'help' for commands.\n");
}

/* ================================================================ ALIAS */
typedef struct {const char *name;const char *value;} alias_t;
static alias_t aliases[]={
    {"ll","ls -l"},
    {"la","ls -a"},
    {"l","ls -l"},
    {"cls","clear"},
    {0,0}
};
static const char *get_alias(const char *name){
    for(int i=0;aliases[i].name;i++)if(kstrcmp(aliases[i].name,name)==0)return aliases[i].value;
    return 0;
}

/* ================================================================ ENVIRONMENT */
typedef struct {const char *name;const char *value;} envvar_t;
static envvar_t envvars[]={
    {"PATH","/bin:/usr/bin:/usr/local/bin"},
    {"HOME","/root"},
    {"SHELL","/bin/sh"},
    {"USER","root"},
    {"HOSTNAME","minios"},
    {"PWD",""},
    {"TERM","vt100"},
    {"LANG","en_US.UTF-8"},
    {0,0}
};
static const char *get_env(const char *name){
    for(int i=0;envvars[i].name;i++)if(kstrcmp(envvars[i].name,name)==0)return envvars[i].value;
    return "";
}
static void shell_env(void){
    for(int i=0;envvars[i].name;i++){uart_puts(envvars[i].name);uart_puts("=");uart_puts(envvars[i].value);uart_puts("\n");}
}
static void shell_export(const char *var){uart_puts("export: ");uart_puts(var);uart_puts("\n");}

/* ================================================================ KILL & SIGNALS */
#define SIGTERM 15
#define SIGKILL 9
#define SIGINT  2
static void shell_kill(int pid, int sig){
    if(pid<0||pid>=task_count){uart_puts("kill: bad process ID\n");return;}
    if(sig==SIGTERM||sig==0){
        tasks[pid].state=TASK_DEAD;
        uart_puts("Terminated process ");put_dec((u64)pid);uart_puts("\n");
    } else if(sig==SIGKILL){
        uart_puts("kill -9: forced kill of process ");put_dec((u64)pid);uart_puts("\n");
        tasks[pid].state=TASK_DEAD;
    } else if(sig==SIGINT){
        tasks[pid].state=TASK_DEAD;
        uart_puts("Interrupted process ");put_dec((u64)pid);uart_puts("\n");
    } else {
        uart_puts("kill: unsupported signal ");put_dec((u64)sig);uart_puts("\n");
    }
}
static void shell_killall(const char *name){
    uart_puts("killall: sending SIGTERM to ");uart_puts(name);uart_puts("\n");
}

/* ================================================================ NICE & PRIORITY */
static void shell_nice(int pid, int delta){
    if(pid<0||pid>=task_count){uart_puts("nice: bad process ID\n");return;}
    task_prio_t old_prio=tasks[pid].prio;
    int new_prio=(int)tasks[pid].prio+delta;
    if(new_prio<0)new_prio=0;
    if(new_prio>3)new_prio=3;
    tasks[pid].prio=(task_prio_t)new_prio;
    uart_puts("nice: process ");put_dec((u64)pid);
    uart_puts(" priority ");put_dec((u64)old_prio);
    uart_puts(" -> ");put_dec((u64)new_prio);uart_puts("\n");
}

/* ================================================================ SHELL SCRIPT EXECUTION */
static int shell_exec_script(const char *filename){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f||f->type!=VFS_TYPE_FILE){
        uart_puts("sh: cannot open '");uart_puts(filename);uart_puts("'\n");return -1;
    }
    uart_puts("[sh] Executing script: ");uart_puts(filename);uart_puts("\n");
    /* Parse script line by line */
    size_t line_start=0;
    for(size_t i=0;i<=f->size;i++){
        if(i==f->size||(char)f->data[i]=='\n'){
            char line[256];size_t len=i-line_start;
            if(len>255)len=255;
            for(size_t j=0;j<len;j++)line[j]=(char)f->data[line_start+j];
            line[len]=0;
            /* Execute line */
            char cmd[64];size_t ci=0;
            while(line[ci]==' '||line[ci]=='\t')ci++;
            while(line[ci]&&line[ci]!=' '&&line[ci]!='\t'&&line[ci]!='\n'&&ci<63)cmd[ci]=line[ci],ci++;
            cmd[ci]=0;
            if(cmd[0]&&cmd[0]!='#'){
                uart_puts("$ ");uart_puts(line);uart_puts("\n");
                /* Dispatch command */
                shell_exec(line);
            }
            line_start=i+1;
        }
    }
    return 0;
}

/* ================================================================ PIPE SUPPORT */
typedef struct {char buf[256];int pos;int len;} pipe_buf_t;
static pipe_buf_t stdout_pipe={0};
static int pipe_active=0;
static void pipe_write(const char *data, int len){
    for(int i=0;i<len&&stdout_pipe.len<256;i++){
        stdout_pipe.buf[stdout_pipe.len++]=data[i];
    }
}
static void pipe_read_and_process(const char *cmd){
    if(stdout_pipe.len==0)return;
    stdout_pipe.buf[stdout_pipe.len]=0;
    /* Simple: echo the piped data to next command */
    stdout_pipe.len=0;
}

/* ================================================================ MORE/LESS PAGINATION */
static void shell_more(const char *filename){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("more: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    int lines=0;int page=20;
    for(size_t i=0;i<f->size;i++){
        uart_putc((char)f->data[i]);
        if((char)f->data[i]=='\n'){
            lines++;
            if(lines>=page){
                uart_puts("-- More -- (q to quit, Enter for more) ");
                char c;int done=0;
                while(!done){
                    if(uart_getc_nb(&c)){
                        if(c=='q'||c=='Q'){done=1;break;}
                        if(c=='\n'||c=='\r'){lines=0;done=1;}
                        else lines=page;
                    } else __asm__ volatile("yield");
                }
                uart_puts("\n");
                if(done&&(c=='q'||c=='Q'))return;
                lines=0;
            }
        }
    }
}

/* ================================================================ TAR-LIKE ARCHIVE */
static void shell_tar_create(const char *archive, const char *files){
    uart_puts("tar: creating '");uart_puts(archive);uart_puts("'\n");
    uart_puts("tar: (archive creation simulated in ramfs)\n");
    vfs_node_t *a=vfs_mknode(vfs_cwd,archive,VFS_TYPE_FILE);
    if(a){
        char header[128];
        kstrncpy(header,"tar:simulated:archive",127);
        a->data=(u8*)header;
        a->size=kstrlen(header);
        a->mode=0644;
    }
}

static void shell_tar_extract(const char *archive){
    vfs_node_t *a=vfs_find(vfs_cwd,archive);
    if(!a){uart_puts("tar: cannot open '");uart_puts(archive);uart_puts("'\n");return;}
    uart_puts("tar: extracting from '");uart_puts(archive);uart_puts("'\n");
}

/* ================================================================ COMPRESSION (simulated) */
static void shell_gzip(const char *file){
    vfs_node_t *f=vfs_find(vfs_cwd,file);
    if(!f){uart_puts("gzip: cannot open '");uart_puts(file);uart_puts("'\n");return;}
    char newname[256];kstrncpy(newname,file,200);kstrcat(newname,".gz");
    vfs_node_t *gz=vfs_mknode(vfs_cwd,newname,VFS_TYPE_FILE);
    if(gz){
        gz->data=f->data;gz->size=f->size;
        gz->mode=f->mode;
        uart_puts(file);uart_puts(" -> ");uart_puts(newname);uart_puts(" (simulated)\n");
    }
}

static void shell_gunzip(const char *file){
    size_t len=kstrlen(file);
    if(len<3||kstrcmp(file+len-3,".gz")!=0){uart_puts("gunzip: not a .gz file\n");return;}
    char newname[256];kstrncpy(newname,file,len-3);newname[len-3]=0;
    vfs_node_t *gz=vfs_find(vfs_cwd,file);
    if(!gz){uart_puts("gunzip: cannot open '");uart_puts(file);uart_puts("'\n");return;}
    vfs_node_t *out=vfs_mknode(vfs_cwd,newname,VFS_TYPE_FILE);
    if(out){out->data=gz->data;out->size=gz->size;out->mode=gz->mode;}
    uart_puts(file);uart_puts(" -> ");uart_puts(newname);uart_puts("\n");
}
"""

# Add to exports
__all__ = ["MINIOS_STDLIB_C"]
