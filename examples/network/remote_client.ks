import network;

func connect_shell(host, port, password) {
    let client = network.Socket(network.AF_INET, network.SOCK_STREAM, 0);
    client.connect([host, port]);
    
    client.send(password, 0);
    let auth_resp = client.recv(256, 0);
    if auth_resp != "OK" {
        print("[-] Auth failed");
        client.close();
        return;
    }
    
    print("[+] Connected!");
    
    while true {
        let cmd = input(f"{host}> ");
        
        if cmd == "exit" {
            client.send("exit", 0);
            break;
        }
        
        client.send(cmd, 0);
        let response = client.recv(8192, 0);
        print(response);
    }
    
    client.close();
}

connect_shell("127.0.0.1", 4444, "admin123");
