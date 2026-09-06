:: native_server - real compiled socket + subprocess server (C backend, no stubs)
:: Usage: kentscript build native_server.ks && ./native_server

func handle(server) {
    let res = system_socket_accept(server);
    let client = res[0];
    let addr = res[1];
    println("[+] Connection from " + addr);
    system_socket_send(client, "auth: ");
    let auth = system_socket_recv(client, 64);
    if auth == "admin123" {
        system_socket_send(client, "OK");
        let cmd = system_socket_recv(client, 1024);
        let out = system_subprocess_run("echo " + cmd, 1, 1);
        system_socket_send(client, out[1]);
    } else {
        system_socket_send(client, "DENIED");
    }
    system_socket_close(client);
}

func main() {
    let server = system_socket_create(2, 1, 6);
    system_socket_setsockopt(server, 1, 2, 1);
    system_socket_bind(server, "0.0.0.0", 4444);
    system_socket_listen(server, 5);
    println("[+] Listening on 0.0.0.0:4444");
    let count = 0;
    while count < 3 {
        handle(server);
        count = count + 1;
    }
    system_socket_close(server);
}

main();
