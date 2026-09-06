:: docker - Docker SDK (subprocess bridge to docker CLI)
::
:: Usage:
::   import docker;
::   let r = docker.ps();
::   print(r["stdout"]);
::
::   docker.pull("nginx");
::   docker.run("nginx", port: "80:80");

func _run(args) {
    let full = ["docker"];
    for a in args { full.push(a); }
    let result = system_subprocess_run(full);
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode};
}

func ps(all) {
    let args = ["ps"];
    if all != none and all { args.push("-a"); }
    return _run(args);
}

func images() {
    return _run(["images"]);
}

func pull(image) {
    print("Pulling " + image + "...");
    return _run(["pull", image]);
}

func run(image, command, detach, name, port, volume, env) {
    let args = ["run"];
    if detach != none and detach { args.push("-d"); }
    if name != none { args.push("--name"); args.push(name); }
    if port != none { args.push("-p"); args.push(port); }
    if volume != none { args.push("-v"); args.push(volume); }
    if env != none { args.push("-e"); args.push(env); }
    args.push(image);
    if command != none { args.push(command); }
    return _run(args);
}

func stop(container) {
    return _run(["stop", container]);
}

func rm(container, force) {
    let args = ["rm"];
    if force != none and force { args.push("-f"); }
    args.push(container);
    return _run(args);
}

func logs(container, tail) {
    let args = ["logs"];
    if tail != none { args.push("--tail"); args.push(str(tail)); }
    args.push(container);
    return _run(args);
}

func exec(container, command) {
    return _run(["exec", container, command]);
}

func compose(args) {
    let full = ["compose"];
    for a in args { full.push(a); }
    return _run(full);
}

func info() {
    return _run(["info"]);
}

export { ps, images, pull, run, stop, rm, logs, exec, compose, info };
