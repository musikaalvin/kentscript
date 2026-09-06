:: KentScript GUI Controller
import "gui";

let win = gui.Window("pyMetasploit Control v5.0");
win.set_theme("dark");

let title = gui.Label("Exploit Manager Active");
let status = gui.Label("Status: Connected to Framework");

func run_exploit() {
    print("Executing payload...");
    status.set_text("Status: EXPLOIT SENT");
}

let exec_btn = gui.Button("Execute Payload", run_exploit);

win.add(title);
win.add(status);
win.add(exec_btn);
win.show();
