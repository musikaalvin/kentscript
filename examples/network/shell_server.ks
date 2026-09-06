:: Remote shell server (modern KentScript socket API)

import socket;
import subprocess;

func start_server(host, port, password) {
    let server = socket.tcp();
    server.set_reuseaddr();
    server.bind(host, port);
    server.listen(5);
    print(f"[*] Listening on {host}:{port}");

    while true {
        let [client, addr] = server.accept();
        print(f"[+] Client: {addr}");

        let auth = client.recv(256);
        if auth != password {
            client.close();
            continue;
        }

        client.send("OK");

        while true {
            let cmd = client.recv(4096);
            if cmd == "" or cmd == "exit" { break; }

            let result = subprocess.run_command(cmd, true, false, true);
            let output = result.stdout;
            if result.returncode != 0 {
                output = result.stderr;
            }

            client.send(output);
        }

        client.close();
    }
}

start_server("0.0.0.0", 4444, "admin123");
