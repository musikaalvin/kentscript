:: network - Low-level networking
:: Security Hardened Version
:: Version: 2.1.0 - Fixed bugs with is_nan and error handling

const AF_INET = 2;
const AF_INET6 = 10;
const AF_UNIX = 1;

const SOCK_STREAM = 1;
const SOCK_DGRAM = 2;
const SOCK_RAW = 3;

const IPPROTO_TCP = 6;
const IPPROTO_UDP = 17;
const IPPROTO_ICMP = 1;

const SOL_SOCKET = 1;
const SO_REUSEADDR = 2;
const SO_KEEPALIVE = 9;
const SO_BROADCAST = 6;
const SO_RCVBUF = 8;
const SO_SNDBUF = 7;

let _network_safe_mode = true;
let _network_allowed_hosts = [];

:: Enable/disable safe mode
func set_safe_mode(enabled) {
    _network_safe_mode = enabled;
}

:: Set allowed hosts for connections
func set_allowed_hosts(hosts) {
    _network_allowed_hosts = hosts;
}

:: Runtime interface - MUST be defined before other functions that use them
func socket_create(family, sock_type, proto) { 
    return system_socket_create(family, sock_type, proto); 
}

func socket_bind(fd, address) { 
    system_socket_bind(fd, address); 
}

func socket_listen(fd, backlog) { 
    system_socket_listen(fd, backlog); 
}

func socket_accept(fd) { 
    return system_socket_accept(fd); 
}

func socket_connect(fd, address) { 
    :: address can be (host, port) tuple or (host, port) as separate args
    :: Handle both formats
    if typeof(address) == "list" && address.length == 2 {
        :: address is [host, port]
        let result = system_socket_connect(fd, address[0], address[1]);
        if result != none {
            raise "Connection failed: " + str(result);
        }
    } else if typeof(address) == "list" && address.length >= 3 {
        :: address is (host, port, more...)
        let result = system_socket_connect(fd, address[0], address[1]);
        if result != none {
            raise "Connection failed: " + str(result);
        }
    } else {
        :: address is a tuple
        let result = system_socket_connect(fd, address);
        if result != none {
            raise "Connection failed: " + str(result);
        }
    }
    return none;
}

func socket_send(fd, data, flags) { 
    return system_socket_send(fd, data, flags); 
}

func socket_recv(fd, bufsize, flags) { 
    return system_socket_recv(fd, bufsize, flags); 
}

func socket_sendto(fd, data, address, flags) { 
    return system_socket_sendto(fd, data, address, flags); 
}

func socket_recvfrom(fd, bufsize, flags) { 
    return system_socket_recvfrom(fd, bufsize, flags); 
}

func socket_close(fd) { 
    system_socket_close(fd); 
}

func socket_setsockopt(fd, level, optname, value) { 
    system_socket_setsockopt(fd, level, optname, value); 
}

func socket_getsockopt(fd, level, optname) { 
    return system_socket_getsockopt(fd, level, optname); 
}

func socket_setblocking(fd, flag) { 
    system_socket_setblocking(fd, flag); 
}

func socket_settimeout(fd, timeout) { 
    system_socket_settimeout(fd, timeout); 
}

func socket_gettimeout(fd) { 
    return system_socket_gettimeout(fd); 
}

func socket_getaddrinfo(host, port, family, sock_type, proto, flags) { 
    return system_socket_getaddrinfo(host, port, family, sock_type, proto, flags); 
}

func socket_gethostname() { 
    return system_socket_gethostname(); 
}

func socket_gethostbyname(hostname) { 
    return system_socket_gethostbyname(hostname); 
}

func socket_gethostbyaddr(ip_address) { 
    return system_socket_gethostbyaddr(ip_address); 
}

func socket_inet_aton(ip_string) { 
    return system_socket_inet_aton(ip_string); 
}

func socket_inet_ntoa(packed_ip) { 
    return system_socket_inet_ntoa(packed_ip); 
}

:: ValidationError class
class ValidationError {
    func init(self, message) {
        self.message = message;
    }
    func to_string(self) {
        return "ValidationError: " + self.message;
    }
}

:: SecurityError class
class SecurityError {
    func init(self, message) {
        self.message = message;
    }
    func to_string(self) {
        return "SecurityError: " + self.message;
    }
}

:: Parse integer with error handling
func _try_parse_int(value) {
    if typeof(value) == "int" {
        return [true, value];
    }
    if typeof(value) != "str" {
        return [false, 0];
    }
    :: Try to parse
    result = system_builtin_int(value);
    if result == 0 && value != "0" {
        :: Check if it's really zero or parsing failed
        :: system_builtin_int returns 0 on failure for non-numeric strings
        return [false, 0];
    }
    return [true, result];
}

:: Validate IP address
func _validate_ip(ip) {
    if ip == none || ip == "" {
        raise "IP address cannot be empty";
    }
    
    let parts = ip.split(".");
    if parts.length != 4 {
        raise "Invalid IP address format: " + ip;
    }
    
    for part in parts {
        let [ok, num] = _try_parse_int(part);
        if !ok || num < 0 || num > 255 {
            raise "Invalid IP address: " + ip;
        }
    }
    
    return true;
}

:: Validate port number
func _validate_port(port) {
    if port == none {
        raise "Port cannot be empty";
    }
    
    let [ok, num] = _try_parse_int(port);
    if !ok {
        raise "Port must be a number";
    }
    
    if num < 1 || num > 65535 {
        raise "Port must be between 1 and 65535";
    }
    
    return true;
}

:: Validate hostname
func _validate_hostname(host) {
    if host == none || host == "" {
        raise "Hostname cannot be empty";
    }
    
    if host.length > 253 {
        raise "Hostname too long";
    }
    
    return true;
}

:: Check if connection to host is allowed
func _check_allowed_host(host) {
    if _network_allowed_hosts.length > 0 {
        let allowed = false;
        
        :: Check exact match
        for allowed_host in _network_allowed_hosts {
            if host == allowed_host {
                allowed = true;
                break;
            }
        }
        
        :: Check domain suffix
        if !allowed {
            for allowed_host in _network_allowed_hosts {
                if host.ends_with("." + allowed_host) {
                    allowed = true;
                    break;
                }
            }
        }
        
        if !allowed {
            raise "Host not in allowed list: " + host;
        }
    }
    
    return true;
}

:: Validate address tuple
func _validate_address(address) {
    if address == none {
        raise "Address cannot be empty";
    }
    
    if typeof(address) == "list" {
        if address.length < 2 {
            raise "Address must be [host, port]";
        }
        
        let host = address[0];
        let port = address[1];
        
        :: Check if it's an IP or hostname
        if host.contains(".") && !host.contains(":") {
            :: Likely IP address
            _validate_ip(host);
        } else if host.contains(":") {
            :: IPv6 - skip validation for now
        } else {
            :: Hostname
            if _network_safe_mode {
                _validate_hostname(host);
                _check_allowed_host(host);
            }
        }
        
        _validate_port(port);
    }
    
    return true;
}

class Socket {
    func init(self, family, sock_type, proto) {
        if family == none { family = AF_INET; }
        if sock_type == none { sock_type = SOCK_STREAM; }
        if proto == none { proto = 0; }
        
        :: Validate family
        if family != AF_INET && family != AF_INET6 && family != AF_UNIX {
            raise "Invalid address family: " + str(family);
        }
        
        :: Validate socket type
        if sock_type != SOCK_STREAM && sock_type != SOCK_DGRAM && sock_type != SOCK_RAW {
            raise "Invalid socket type: " + str(sock_type);
        }
        
        self.family = family;
        self.sock_type = sock_type;
        self.proto = proto;
        self.fd = socket_create(family, sock_type, proto);
    }
    
    func bind(self, address) {
        _validate_address(address);
        socket_bind(self.fd, address);
    }
    
    func listen(self, backlog) {
        if backlog == none { backlog = 5; }
        if _network_safe_mode && (backlog < 1 || backlog > 128) {
            raise "Backlog must be between 1 and 128";
        }
        socket_listen(self.fd, backlog);
    }
    
    func accept(self) {
        let [client_fd, addr] = socket_accept(self.fd);
        let client = Socket(AF_INET, SOCK_STREAM, 0);
        client.fd = client_fd;
        return [client, addr];
    }
    
    func connect(self, address) {
        _validate_address(address);
        
        if _network_safe_mode && address[0] != none {
            let host = address[0];
            
            :: Check for private/internal IPs
            if host == "127.0.0.1" || host == "localhost" || host == "0.0.0.0" {
                :: Local connections allowed
            } else if host.starts_with("192.168.") || host.starts_with("10.") {
                raise "Cannot connect to private IP: " + host;
            } else if host.starts_with("172.") {
                let [ok, second] = _try_parse_int(host.split(".")[1]);
                if ok && second >= 16 && second <= 31 {
                    raise "Cannot connect to private IP: " + host;
                }
            }
        }
        
        :: This will raise an exception on failure
        socket_connect(self.fd, address);
    }
    
    func send(self, data, flags) {
        if data == none || data == "" {
            raise "Data cannot be empty";
        }
        if flags == none { flags = 0; }
        
        if _network_safe_mode && data.length > 1024 * 1024 {
            raise "Data too large (max 1MB)";
        }
        
        return socket_send(self.fd, data, flags);
    }
    
    func recv(self, bufsize, flags) {
        if bufsize == none || bufsize <= 0 {
            raise "Invalid buffer size";
        }
        
        if _network_safe_mode && bufsize > 1024 * 1024 {
            raise "Buffer size too large (max 1MB)";
        }
        
        if flags == none { flags = 0; }
        return socket_recv(self.fd, bufsize, flags);
    }
    
    func sendto(self, data, address, flags) {
        if data == none || data == "" {
            raise "Data cannot be empty";
        }
        _validate_address(address);
        if flags == none { flags = 0; }
        return socket_sendto(self.fd, data, address, flags);
    }
    
    func recvfrom(self, bufsize, flags) {
        if bufsize == none || bufsize <= 0 {
            raise "Invalid buffer size";
        }
        
        if _network_safe_mode && bufsize > 1024 * 1024 {
            raise "Buffer size too large (max 1MB)";
        }
        
        if flags == none { flags = 0; }
        return socket_recvfrom(self.fd, bufsize, flags);
    }
    
    func sendall(self, data) {
        let total = 0;
        while total < data.length {
            let sent = self.send(data.slice(total), 0);
            if sent == 0 {
                raise "Socket connection broken";
            }
            total = total + sent;
        }
    }
    
    func close(self) {
        if self.fd != none {
            socket_close(self.fd);
            self.fd = none;
        }
    }
    
    func setsockopt(self, level, optname, value) {
        socket_setsockopt(self.fd, level, optname, value);
    }
    
    func getsockopt(self, level, optname) {
        return socket_getsockopt(self.fd, level, optname);
    }
    
    func setblocking(self, flag) {
        socket_setblocking(self.fd, flag);
    }
    
    func settimeout(self, timeout) {
        socket_settimeout(self.fd, timeout);
    }
    
    func gettimeout(self) {
        return socket_gettimeout(self.fd);
    }
    
    func fileno(self) {
        return self.fd;
    }
}

func create_connection(address, timeout, source_address) {
    let sock = Socket(AF_INET, SOCK_STREAM, 0);
    
    if timeout != none {
        sock.settimeout(timeout);
    }
    
    if source_address != none {
        sock.bind(source_address);
    }
    
    sock.connect(address);
    return sock;
}

func create_server(address, family, backlog, reuse_port) {
    if family == none { family = AF_INET; }
    if backlog == none { backlog = 5; }
    if reuse_port == none { reuse_port = false; }
    
    let sock = Socket(family, SOCK_STREAM, 0);
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1);
    
    if reuse_port {
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1);
    }
    
    sock.bind(address);
    sock.listen(backlog);
    return sock;
}

func getaddrinfo(host, port, family, sock_type, proto, flags) {
    return socket_getaddrinfo(host, port, family, sock_type, proto, flags);
}

func gethostname() {
    return socket_gethostname();
}

func gethostbyname(hostname) {
    return socket_gethostbyname(hostname);
}

func gethostbyaddr(ip_address) {
    return socket_gethostbyaddr(ip_address);
}

func inet_aton(ip_string) {
    return socket_inet_aton(ip_string);
}

func inet_ntoa(packed_ip) {
    return socket_inet_ntoa(packed_ip);
}

func htons(x) {
    return x;
}

func ntohs(x) {
    return x;
}

func htonl(x) {
    return x;
}

func ntohl(x) {
    return x;
}

export {
    Socket,
    create_connection, create_server,
    getaddrinfo, gethostname, gethostbyname, gethostbyaddr,
    inet_aton, inet_ntoa, htons, ntohs, htonl, ntohl,
    AF_INET, AF_INET6, AF_UNIX,
    SOCK_STREAM, SOCK_DGRAM, SOCK_RAW,
    IPPROTO_TCP, IPPROTO_UDP, IPPROTO_ICMP,
    SOL_SOCKET, SO_REUSEADDR, SO_KEEPALIVE, SO_BROADCAST, SO_RCVBUF, SO_SNDBUF,
    
    :: Security
    set_safe_mode, set_allowed_hosts
};
