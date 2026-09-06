:: socket - TCP/UDP Socket Interface
::
:: Usage:
::   import socket;
::
::   :: TCP Client
::   let s = socket.tcp();
::   s.connect("example.com", 80);
::   s.send("GET / HTTP/1.1\r\nHost: example.com\r\n\r\n");
::   let data = s.recv(1024);
::   s.close();
::
::   :: TCP Server
::   let srv = socket.tcp();
::   srv.bind("0.0.0.0", 8080);
::   srv.listen(5);
::   let [client, addr] = srv.accept();
::   let msg = client.recv(1024);
::   client.send("Hello!");
::   client.close();
::   srv.close();

let AF_INET = 2;
let AF_INET6 = 10;
let AF_UNIX = 1;
let SOCK_STREAM = 1;
let SOCK_DGRAM = 2;
let IPPROTO_TCP = 6;
let IPPROTO_UDP = 17;
let SOL_SOCKET = 1;
let SO_REUSEADDR = 2;
let SO_KEEPALIVE = 9;

class TCPSocket {
    func __init__(self, sock=none) {
        if sock == none {
            self._sock = system_socket_create(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        } else {
            self._sock = sock;
        }
    }

    func connect(self, host, port) {
        system_socket_connect(self._sock, host, port);
    }

    func bind(self, host, port) {
        system_socket_bind(self._sock, [host, port]);
    }

    func listen(self, backlog) {
        if backlog == none { backlog = 5; }
        system_socket_listen(self._sock, backlog);
    }

    func accept(self) {
        let result = system_socket_accept(self._sock);
        let client = TCPSocket(result[0]);
        return [client, result[1]];
    }

    func send(self, data) {
        if type(data) == "string" {
            data = data.encode();
        }
        return system_socket_send(self._sock, data);
    }

    func recv(self, bufsize) {
        if bufsize == none { bufsize = 4096; }
        return system_socket_recv(self._sock, bufsize);
    }

    func close(self) {
        system_socket_close(self._sock);
    }

    func set_timeout(self, timeout) {
        system_socket_settimeout(self._sock, timeout);
    }

    func set_nonblocking(self, flag) {
        system_socket_setblocking(self._sock, flag);
    }

    func set_reuseaddr(self) {
        system_socket_setsockopt(self._sock, SOL_SOCKET, SO_REUSEADDR, 1);
    }
}

class UDPSocket {
    func __init__(self) {
        self._sock = system_socket_create(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    }

    func bind(self, host, port) {
        system_socket_bind(self._sock, [host, port]);
    }

    func sendto(self, data, host, port) {
        if type(data) == "string" {
            data = data.encode();
        }
        return system_socket_sendto(self._sock, data, [host, port], 0);
    }

    func recvfrom(self, bufsize) {
        if bufsize == none { bufsize = 4096; }
        return system_socket_recvfrom(self._sock, bufsize, 0);
    }

    func close(self) {
        system_socket_close(self._sock);
    }

    func set_timeout(self, timeout) {
        system_socket_settimeout(self._sock, timeout);
    }
}

func tcp() {
    return TCPSocket();
}

func udp() {
    return UDPSocket();
}

func gethostname() {
    return system_socket_gethostname();
}

func gethostbyname(hostname) {
    return system_socket_gethostbyname(hostname);
}

func getaddrinfo(host, port) {
    return system_socket_getaddrinfo(host, port, 0, 0, 0, 0);
}

func inet_aton(ip) {
    return system_socket_inet_aton(ip);
}

func inet_ntoa(packed) {
    return system_socket_inet_ntoa(packed);
}

export {
    AF_INET, AF_INET6, AF_UNIX,
    SOCK_STREAM, SOCK_DGRAM,
    IPPROTO_TCP, IPPROTO_UDP,
    SOL_SOCKET, SO_REUSEADDR, SO_KEEPALIVE,
    TCPSocket, UDPSocket,
    tcp, udp,
    gethostname, gethostbyname, getaddrinfo,
    inet_aton, inet_ntoa
};
