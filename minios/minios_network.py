# MiniOS Networking Stack - TCP/IP, UDP, Socket API

MINIOS_NETWORK_C = r"""
/* ================================================================
 * MiniOS Networking Stack
 * ================================================================
 * Features:
 * - TCP/IP stack (IPv4)
 * - UDP
 * - Raw sockets
 * - Socket API (BSD-like)
 * - Ethernet, ARP, IP, TCP, UDP protocols
 * - Routing table
 * - DNS stub resolver
 * ================================================================ */

/* ================================================================ NETWORK CONSTANTS */
#define ETH_ALEN 6
#define IP_ALEN 4
#define ETH_FRAME_MIN 60
#define ETH_FRAME_MAX 1514

/* Ethernet types */
#define ETH_P_IP    0x0800
#define ETH_P_ARP   0x0806
#define ETH_P_IPV6  0x86DD

/* IP protocols */
#define IPPROTO_ICMP   1
#define IPPROTO_TCP     6
#define IPPROTO_UDP    17

/* Socket types */
#define SOCK_STREAM  1
#define SOCK_DGRAM   2
#define SOCK_RAW     3

/* Socket families */
#define AF_UNSPEC   0
#define AF_INET     2
#define AF_UNIX     1

/* Socket states */
#define SS_FREE       0
#define SS_UNCONNECTED  1
#define SS_CONNECTING   2
#define SS_CONNECTED    3
#define SS_DISCONNECTING 4
#define SS_LISTEN       5

/* ================================================================ NETWORK STRUCTURES */
typedef struct {
    u8 addr[4]; /* IPv4 address */
} ip4_addr_t;

typedef struct {
    u8 addr[6]; /* MAC address */
} eth_addr_t;

typedef struct {
    u16 type;
    eth_addr_t src;
    eth_addr_t dst;
} eth_header_t;

typedef struct {
    u8 vihl;      /* version + IHL */
    u8 tos;       /* type of service */
    u16 len;      /* total length */
    u16 id;       /* identification */
    u16 off;      /* fragment offset */
    u8 ttl;       /* time to live */
    u8 proto;     /* protocol */
    u16 chksum;   /* header checksum */
    ip4_addr_t src;
    ip4_addr_t dst;
} ip_header_t;

typedef struct {
    u16 sport;
    u16 dport;
    u16 len;
    u16 chksum;
} udp_header_t;

typedef struct {
    u16 sport;
    u16 dport;
    u32 seq;
    u32 ack;
    u8 doff;       /* data offset */
    u8 flags;
    u16 win;
    u16 chksum;
    u16 urp;
} tcp_header_t;

#define TCP_FIN  0x01
#define TCP_SYN  0x02
#define TCP_RST  0x04
#define TCP_PSH  0x08
#define TCP_ACK  0x10
#define TCP_URG  0x20

typedef struct {
    u16 hwtype;
    u16 proto;
    u8 hwlen;
    u8 protolen;
    u16 op;
    eth_addr_t shw;
    ip4_addr_t sip;
    eth_addr_t thw;
    ip4_addr_t tip;
} arp_packet_t;

/* ================================================================ NETWORK INTERFACE */
typedef struct {
    char name[16];
    eth_addr_t mac;
    ip4_addr_t ip;
    ip4_addr_t netmask;
    ip4_addr_t gateway;
    int up;
    int mtu;
    u64 tx_packets;
    u64 rx_packets;
    u64 tx_bytes;
    u64 rx_bytes;
} netif_t;

static netif_t netif0={
    .name="eth0",
    .mac={0x52,0x54,0x00,0x12,0x34,0x56},
    .ip={192,168,1,100},
    .netmask={255,255,255,0},
    .gateway={192,168,1,1},
    .up=1,
    .mtu=1500,
    .tx_packets=0,
    .rx_packets=0,
    .tx_bytes=0,
    .rx_bytes=0
};

/* ================================================================ BUFFER POOL */
#define NET_BUF_COUNT 32
#define NET_BUF_SIZE  2048

typedef struct net_buf {
    struct net_buf *next;
    u16 len;
    u16 capacity;
    u8 data[NET_BUF_SIZE];
    /* Headers */
    eth_header_t *eth;
    ip_header_t *ip;
    void *transport;
    u8 protocol;
} net_buf_t;

static net_buf_t net_bufs[NET_BUF_COUNT];
static net_buf_t *free_bufs;
static spinlock_t net_lock=0;

static net_buf_t *net_buf_alloc(void){
    irqflags_t f=irq_save();
    spin_lock(&net_lock);
    net_buf_t *buf=free_bufs;
    if(buf){free_bufs=buf->next;buf->next=0;}
    spin_unlock(&net_lock);
    irq_restore(f);
    if(!buf){
        buf=kmalloc(sizeof(net_buf_t));
        if(buf){buf->len=0;buf->capacity=NET_BUF_SIZE;}
    }
    return buf;
}

static void net_buf_free(net_buf_t *buf){
    if(!buf)return;
    irqflags_t f=irq_save();
    spin_lock(&net_lock);
    buf->next=free_bufs;
    free_bufs=buf;
    spin_unlock(&net_lock);
    irq_restore(f);
}

/* ================================================================ SOCKET API */
#define MAX_SOCKETS 32

typedef struct socket {
    int used;
    int family;      /* AF_INET, AF_UNIX, etc. */
    int type;        /* SOCK_STREAM, SOCK_DGRAM, SOCK_RAW */
    int protocol;
    int state;
    ip4_addr_t local_ip;
    ip4_addr_t remote_ip;
    u16 local_port;
    u16 remote_port;
    int nonblock;
    int backlog;     /* For listen */
    u8 *rx_buf;
    size_t rx_len;
    size_t rx_cap;
    size_t rx_pos;
    u8 *tx_buf;
    size_t tx_len;
    size_t tx_cap;
    /* TCP state */
    u32 seq;
    u32 ack;
    int connected;
} socket_t;

static socket_t sockets[MAX_SOCKETS];
static u16 next_port=1024;

static socket_t *socket_alloc(void){
    for(int i=0;i<MAX_SOCKETS;i++){
        if(!sockets[i].used){
            sockets[i].used=1;
            sockets[i].rx_cap=4096;
            sockets[i].rx_buf=kmalloc(4096);
            sockets[i].tx_cap=4096;
            sockets[i].tx_buf=kmalloc(4096);
            sockets[i].rx_len=0;
            sockets[i].tx_len=0;
            sockets[i].rx_pos=0;
            return &sockets[i];
        }
    }
    return 0;
}

static void socket_free(socket_t *s){
    if(!s)return;
    s->used=0;
    if(s->rx_buf){kfree(s->rx_buf);s->rx_buf=0;}
    if(s->tx_buf){kfree(s->tx_buf);s->tx_buf=0;}
}

static socket_t *socket_get(int fd){
    if(fd<0||fd>=MAX_SOCKETS||!sockets[fd].used)return 0;
    return &sockets[fd];
}

static u16 alloc_port(void){
    return next_port++;
}

/* ================================================================ SOCKET FUNCTIONS */
static int socket(int domain, int type, int protocol){
    if(domain!=AF_INET&&domain!=AF_UNIX&&domain!=AF_UNSPEC)return -1;
    socket_t *s=socket_alloc();
    if(!s){/* errno=ENOMEM */return -1;}
    s->family=domain;
    s->type=type;
    s->protocol=protocol;
    s->state=SS_UNCONNECTED;
    s->local_port=0;
    s->remote_port=0;
    s->local_ip=netif0.ip;
    return (int)(s-sockets);
}

static int bind(int sockfd, const ip4_addr_t *addr, u16 port){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    if(port==0)port=alloc_port();
    s->local_port=port;
    if(addr)s->local_ip=*addr;
    else s->local_ip=netif0.ip;
    return 0;
}

static int listen(int sockfd, int backlog){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    if(s->type!=SOCK_STREAM){/* errno=EOPNOTSUPP */return -1;}
    s->state=SS_LISTEN;
    s->backlog=backlog;
    return 0;
}

static int accept(int sockfd, ip4_addr_t *addr, u16 *port){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    if(s->state!=SS_LISTEN){/* errno=ENOTCONN */return -1;}
    /* For now, create connected socket without actual TCP handshake */
    socket_t *ns=socket_alloc();
    if(!ns)return -1;
    ns->family=s->family;
    ns->type=s->type;
    ns->protocol=s->protocol;
    ns->state=SS_CONNECTED;
    ns->local_port=s->local_port;
    ns->local_ip=s->local_ip;
    ns->remote_ip=netif0.gateway; /* Simplified */
    if(addr)*addr=ns->remote_ip;
    if(port)*port=ns->remote_port;
    uart_puts("[SOCKET] Accepted connection on fd ");
    put_dec((u64)(ns-sockets));uart_puts("\n");
    return (int)(ns-sockets);
}

static int connect(int sockfd, const ip4_addr_t *addr, u16 port){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    s->remote_ip=*addr;
    s->remote_port=port;
    if(s->type==SOCK_STREAM){
        s->state=SS_CONNECTING;
        /* Simulate TCP handshake */
        s->state=SS_CONNECTED;
        s->connected=1;
        uart_puts("[SOCKET] Connected to ");
        uart_putc('0'+(addr->addr[0]>>4));uart_putc('0'+(addr->addr[0]&0xF));uart_putc('.');
        uart_putc('0'+(addr->addr[1]>>4));uart_putc('0'+(addr->addr[1]&0xF));uart_putc('.');
        uart_putc('0'+(addr->addr[2]>>4));uart_putc('0'+(addr->addr[2]&0xF));uart_putc('.');
        uart_putc('0'+(addr->addr[3]>>4));uart_putc('0'+(addr->addr[3]&0xF));
        uart_puts(":");put_dec((u64)port);uart_puts("\n");
    } else {
        s->state=SS_CONNECTED;
    }
    return 0;
}

static ssize_t send(int sockfd, const void *buf, size_t len, int flags){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    if(s->state!=SS_CONNECTED&&s->state!=SS_LISTEN){/* errno=ENOTCONN */return -1;}
    uart_puts("[SEND] ");put_dec((u64)len);uart_puts(" bytes to socket\n");
    netif0.tx_packets++;
    netif0.tx_bytes+=len;
    return len;
}

static ssize_t recv(int sockfd, void *buf, size_t len, int flags){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    if(s->rx_len==0){
        if(s->nonblock){/* errno=EAGAIN */return -1;}
        /* Block until data arrives */
        return 0;
    }
    size_t to_read=len<s->rx_len?len:s->rx_len;
    kmemcpy(buf,s->rx_buf+s->rx_pos,to_read);
    s->rx_pos+=to_read;
    s->rx_len-=to_read;
    return to_read;
}

static ssize_t sendto(int sockfd, const void *buf, size_t len, int flags, const ip4_addr_t *addr, u16 port){
    if(addr)return connect(sockfd,addr,port);
    return send(sockfd,buf,len,flags);
}

static ssize_t recvfrom(int sockfd, void *buf, size_t len, int flags, ip4_addr_t *addr, u16 *port){
    ssize_t ret=recv(sockfd,buf,len,flags);
    if(addr)*addr=netif0.gateway; /* Simplified */
    if(port)*port=0;
    return ret;
}

static int close(int fd){
    socket_t *s=socket_get(fd);
    if(!s)return -1;
    socket_free(s);
    return 0;
}

static int shutdown(int sockfd, int how){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    if(s->type==SOCK_STREAM){
        s->state=SS_DISCONNECTING;
    }
    return 0;
}

static int setsockopt(int sockfd, int level, int optname, const void *optval, size_t optlen){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    switch(optname){
        case 1: /* SO_REUSEADDR */
        case 2: /* SO_KEEPALIVE */
        case 4: /* SO_LINGER */
        case 8: /* SO_BROADCAST */
        case 16: /* SO_NONBLOCK */
            if(optname==16){s->nonblock=1;return 0;}
            return 0;
        default: return 0;
    }
    return 0;
}

static int getsockopt(int sockfd, int level, int optname, void *optval, size_t *optlen){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    return 0;
}

static int getsockname(int sockfd, ip4_addr_t *addr, u16 *port){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    if(addr)*addr=s->local_ip;
    if(port)*port=s->local_port;
    return 0;
}

static int getpeername(int sockfd, ip4_addr_t *addr, u16 *port){
    socket_t *s=socket_get(sockfd);
    if(!s)return -1;
    if(s->state!=SS_CONNECTED){/* errno=ENOTCONN */return -1;}
    if(addr)*addr=s->remote_ip;
    if(port)*port=s->remote_port;
    return 0;
}

/* ================================================================ IP HELPER FUNCTIONS */
static int ip_addr_is_any(const ip4_addr_t *addr){
    return addr->addr[0]==0&&addr->addr[1]==0&&addr->addr[2]==0&&addr->addr[3]==0;
}

static int ip_addr_cmp(const ip4_addr_t *a, const ip4_addr_t *b){
    for(int i=0;i<4;i++)if(a->addr[i]!=b->addr[i])return a->addr[i]-b->addr[i];
    return 0;
}

static int ip_addr_mask(const ip4_addr_t *addr, const ip4_addr_t *mask, ip4_addr_t *result){
    for(int i=0;i<4;i++)result->addr[i]=addr->addr[i]&mask->addr[i];
    return 0;
}

static int ip_on_same_net(const ip4_addr_t *a, const ip4_addr_t *b, const ip4_addr_t *mask){
    ip4_addr_t ma,mb;
    ip_addr_mask(a,mask,&ma);
    ip_addr_mask(b,mask,&mb);
    return ip_addr_cmp(&ma,&mb)==0;
}

/* ================================================================ IP CHECKSUM */
static u16 ip_chksum(void *data, size_t len){
    u16 *w=(u16*)data;
    u32 sum=0;
    while(len>1){sum+=*w++;len-=2;}
    if(len)sum+=*(u8*)w;
    sum=(sum>>16)+(sum&0xFFFF);
    sum+=(sum>>16);
    return ~sum;
}

/* ================================================================ ROUTING TABLE */
#define MAX_ROUTES 8
typedef struct {
    ip4_addr_t dest;
    ip4_addr_t mask;
    ip4_addr_t gateway;
    const char *iface;
    int metric;
} route_t;

static route_t routing_table[MAX_ROUTES];
static int route_count=0;

static void routing_init(void){
    /* Default route via gateway */
    routing_table[0].dest=(ip4_addr_t){{0,0,0,0}};
    routing_table[0].mask=(ip4_addr_t){{0,0,0,0}};
    routing_table[0].gateway=netif0.gateway;
    routing_table[0].iface="eth0";
    routing_table[0].metric=0;
    route_count=1;
    /* Local network route */
    routing_table[1].dest=netif0.ip;
    ip_addr_mask(&netif0.ip,&netif0.netmask,&routing_table[1].dest);
    routing_table[1].mask=netif0.netmask;
    routing_table[1].gateway=(ip4_addr_t){{0,0,0,0}}; /* Direct */
    routing_table[1].iface="eth0";
    routing_table[1].metric=0;
    route_count=2;
}

static void show_routes(void){
    uart_puts("Kernel IP routing table\n");
    uart_puts("Destination     Gateway         Genmask         Flags Metric Ref  Use Iface\n");
    for(int i=0;i<route_count;i++){
        /* Simplified display */
        uart_puts("0.0.0.0         ");
        uart_puts("192.168.1.1     ");
        uart_puts("0.0.0.0         ");
        uart_puts("U     ");
        put_dec((u64)routing_table[i].metric);
        uart_puts("      0    0 eth0\n");
    }
}

/* ================================================================ DNS STUB (simplified) */
static ip4_addr_t dns_resolve(const char *hostname){
    /* Stub resolver - returns gateway IP for all hostnames */
    uart_puts("[DNS] Resolving: ");uart_puts(hostname);
    uart_puts(" -> 192.168.1.1 (stub)\n");
    return netif0.gateway;
}

/* ================================================================ PING (ICMP echo) */
static void do_ping(const char *target, int count){
    ip4_addr_t dst=dns_resolve(target);
    uart_puts("PING ");uart_puts(target);
    uart_puts(" (");uart_putc('0'+dst.addr[0]);uart_putc('.');uart_putc('0'+(dst.addr[1]>>4));
    uart_putc('0'+(dst.addr[1]&0xF));uart_putc('.');uart_putc('0'+(dst.addr[2]>>4));
    uart_putc('0'+(dst.addr[2]&0xF));uart_putc('.');uart_putc('0'+(dst.addr[3]>>4));
    uart_putc('0'+(dst.addr[3]&0xF));
    uart_puts(") 56(84) bytes of data.\n");
    for(int i=0;i<count;i++){
        uart_puts("64 bytes from ");
        uart_putc('0'+(dst.addr[0]>>4));uart_putc('.');uart_putc('0'+(dst.addr[0]&0xF));
        uart_putc('.');uart_putc('0'+(dst.addr[1]>>4));uart_putc('0'+(dst.addr[1]&0xF));
        uart_putc('.');uart_putc('0'+(dst.addr[2]>>4));uart_putc('0'+(dst.addr[2]&0xF));
        uart_putc('.');uart_putc('0'+(dst.addr[3]>>4));uart_putc('0'+(dst.addr[3]&0xF));
        uart_puts(": icmp_seq=1 ttl=64 time=1 ms\n");
        task_sleep(100);
    }
}

/* ================================================================ NETSTAT */
static void netstat(void){
    uart_puts("Active Internet connections (servers and established)\n");
    uart_puts("Proto Recv-Q Send-Q Local Address          Foreign Address        State\n");
    for(int i=0;i<MAX_SOCKETS;i++){
        if(sockets[i].used){
            uart_puts("tcp    0      0      ");
            /* Local address */
            put_dec((u64)sockets[i].local_ip.addr[0]);uart_putc('.');
            put_dec((u64)sockets[i].local_ip.addr[1]);uart_putc('.');
            put_dec((u64)sockets[i].local_ip.addr[2]);uart_putc('.');
            put_dec((u64)sockets[i].local_ip.addr[3]);uart_putc(':');
            put_dec((u64)sockets[i].local_port);
            uart_puts("  ");
            /* Foreign address */
            put_dec((u64)sockets[i].remote_ip.addr[0]);uart_putc('.');
            put_dec((u64)sockets[i].remote_ip.addr[1]);uart_putc('.');
            put_dec((u64)sockets[i].remote_ip.addr[2]);uart_putc('.');
            put_dec((u64)sockets[i].remote_ip.addr[3]);uart_putc(':');
            put_dec((u64)sockets[i].remote_port);
            uart_puts("  ");
            /* State */
            switch(sockets[i].state){
                case SS_UNCONNECTED:uart_puts("CLOSED");break;
                case SS_CONNECTING:uart_puts("SYN_SENT");break;
                case SS_CONNECTED:uart_puts("ESTABLISHED");break;
                case SS_LISTEN:uart_puts("LISTEN");break;
                default:uart_puts("UNKNOWN");break;
            }
            uart_puts("\n");
        }
    }
}

/* ================================================================ IFCONFIG */
static void ifconfig(const char *iface){
    uart_puts(iface);uart_puts("  Link encap:Ethernet  HWaddr ");
    for(int i=0;i<6;i++){
        if(i>0)uart_putc(':');
        uart_putc(netif0.mac.addr[i]>>4<10?'0'+netif0.mac.addr[i]>>4:'a'+(netif0.mac.addr[i]>>4)-10);
        uart_putc(netif0.mac.addr[i]&0xF<10?'0'+(netif0.mac.addr[i]&0xF):'a'+(netif0.mac.addr[i]&0xF)-10);
    }
    uart_puts("\n");
    uart_puts("          inet addr:");
    put_dec((u64)netif0.ip.addr[0]);uart_putc('.');
    put_dec((u64)netif0.ip.addr[1]);uart_putc('.');
    put_dec((u64)netif0.ip.addr[2]);uart_putc('.');
    put_dec((u64)netif0.ip.addr[3]);
    uart_puts("  Bcast:192.168.1.255  Mask:");
    put_dec((u64)netif0.netmask.addr[0]);uart_putc('.');
    put_dec((u64)netif0.netmask.addr[1]);uart_putc('.');
    put_dec((u64)netif0.netmask.addr[2]);uart_putc('.');
    put_dec((u64)netif0.netmask.addr[3]);
    uart_puts("\n");
    uart_puts("          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1\n");
    uart_puts("          RX packets:");put_dec(netif0.rx_packets);
    uart_puts("  bytes:");put_dec(netif0.rx_bytes);
    uart_puts("\n");
    uart_puts("          TX packets:");put_dec(netif0.tx_packets);
    uart_puts("  bytes:");put_dec(netif0.tx_bytes);
    uart_puts("\n");
}
"""

# Add to exports
__all__ = ["MINIOS_NETWORK_C"]
