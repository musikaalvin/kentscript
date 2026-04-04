:: subprocess - Process execution and management
:: Version: 2.5.0 - Simplified to avoid interpreter bugs

let _subprocess_safe_mode = true;

func set_safe_mode(enabled) {
    _subprocess_safe_mode = enabled;
}

class CompletedProcess {
    func init(args, returncode, stdout, stderr) {
        self.args = args;
        self.returncode = returncode;
        self.stdout = stdout;
        self.stderr = stderr;
    }
}

func _make_completed(args, returncode, stdout, stderr) {
    let proc = new CompletedProcess(args, returncode, stdout, stderr);
    return proc;
}

func run_command(cmd, capture_output, check, shell) {
    if capture_output == none { capture_output = true; }
    if check == none { check = false; }
    if shell == none { shell = true; }
    
    if _subprocess_safe_mode {
        if cmd.contains(";") || cmd.contains("&&") || cmd.contains("||") {
            raise "Shell operators not allowed in safe mode";
        }
        if cmd.contains("|") {
            raise "Pipes not allowed in safe mode";
        }
    }
    
    let result = _execute(cmd, shell, capture_output);
    
    if check && result.returncode != 0 {
        raise "Command failed with exit code: " + str(result.returncode);
    }
    
    return result;
}

func _execute(cmd, shell, capture_output) {
    if capture_output {
        result = system_subprocess_run(cmd, shell, true);
        return _make_completed(cmd, result.returncode, result.stdout, result.stderr);
    } else {
        result = system_subprocess_run(cmd, shell, false);
        return _make_completed(cmd, result.returncode, "", "");
    }
}

func call(cmd, shell) {
    if shell == none { shell = true; }
    result = run_command(cmd, false, false, shell);
    return result.returncode;
}

func check_call(cmd, shell) {
    if shell == none { shell = true; }
    result = run_command(cmd, false, true, shell);
    return result.returncode;
}

func check_output(cmd) {
    result = run_command(cmd, true, true, true);
    return result.stdout;
}

func getoutput(cmd) {
    result = run_command(cmd, true, false, true);
    return result.stdout;
}

const PIPE = -1;
const STDOUT = -2;
const DEVNULL = -3;

export {
    run_command, call, check_call, check_output, getoutput,
    CompletedProcess,
    PIPE, STDOUT, DEVNULL,
    set_safe_mode
};
