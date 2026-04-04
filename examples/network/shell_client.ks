:: Remote shell client

func connect_shell(host, port, password) {
    let client = system_socket_create(2, 1, 0);
    system_socket_connect(client, [host, port]);
    
    system_socket_send(client, password, 0);
    let auth_resp = system_socket_recv(client, 256, 0);
    if auth_resp != "OK" {
        print("[-] Auth failed");
        system_socket_close(client);
        return;
    }
    
    print("[+] Connected!");
    
    while true {
        let cmd = input(f"{host}> ");
        
        if cmd == "exit" {
            system_socket_send(client, "exit", 0);
            break;
        }
        
        system_socket_send(client, cmd, 0);
        let response = system_socket_recv(client, 8192, 0);
        print(response);
    }
    
    system_socket_close(client);
}

connect_shell("127.0.0.1", 4444, "admin123");
