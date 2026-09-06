:: ssh - SSH client (subprocess bridge to system ssh)
::
:: Usage:
::   import ssh;
::   let r = ssh.run("user@host", "ls -la");
::   print(r["stdout"]);
::
::   let r = ssh.scp("local.txt", "user@host:/remote/path/");

func run(host, command, port, key_path) {
    let args = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"];
    if port != none { args.push("-p"); args.push(str(port)); }
    if key_path != none { args.push("-i"); args.push(key_path); }
    args.push(host);
    args.push(command);
    let result = system_subprocess_run(args);
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode, "args": result.args};
}

func scp(source, dest, port, key_path) {
    let args = ["scp", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"];
    if port != none { args.push("-P"); args.push(str(port)); }
    if key_path != none { args.push("-i"); args.push(key_path); }
    args.push(source);
    args.push(dest);
    let result = system_subprocess_run(args);
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode};
}

func shell(host, port, key_path) {
    let args = ["ssh", "-o", "StrictHostKeyChecking=no"];
    if port != none { args.push("-p"); args.push(str(port)); }
    if key_path != none { args.push("-i"); args.push(key_path); }
    args.push(host);
    println("Connecting to " + host + "...");
    println("Run: " + args.join(" "));
    let result = system_subprocess_run(args);
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode};
}

export { run, scp, shell };
