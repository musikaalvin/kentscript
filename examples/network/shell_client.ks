:: Remote shell client (modern KentScript socket API)

import socket;

func connect_shell(host, port, password) {
    let client = socket.tcp();
    client.connect(host, port);

    client.send(password);
    let auth_resp = client.recv(256);
    if auth_resp != "OK" {
        print("[-] Auth failed");
        client.close();
        return;
    }

    print("[+] Connected!");

    while true {
        let cmd = input(f"{host}> ");

        if cmd == "exit" {
            client.send("exit");
            break;
        }

        client.send(cmd);
        let response = client.recv(8192);
        print(response);
    }

    client.close();
}

connect_shell("127.0.0.1", 4444, "admin123");
