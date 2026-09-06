:: MiniOS Component written in KentScript
:: This demonstrates building OS components in KentScript syntax

func kmalloc(size) {
    let ptr = malloc(size);
    return ptr;
}

func kstrlen(s) {
    let i = 0;
    while i < s.len() {
        if s[i] == 0 {
            return i;
        }
        i = i + 1;
    }
    return 0;
}

func uart_puts(msg) {
    let i = 0;
    while i < msg.len() {
        print(msg[i]);
        i = i + 1;
    }
}

func show_task_info(pid, name, ticks) {
    print("Task: ");
    print(name);
    print(" PID:");
    print(pid);
    print(" ticks:");
    print(ticks);
    print("\n");
}

func minios_main() {
    print("=== MiniOS KentScript Component ===\n");
    print("Written in KentScript syntax!\n");
    print("Compiles to C -> builds to ELF\n");
    print("================================\n");
    
    let buf = kmalloc(64);
    if buf != 0 {
        print("[OK] kmalloc working\n");
    }
    
    show_task_info(1, "init", 100);
    show_task_info(2, "shell", 50);
    
    print("\nKentScript OS ready!\n");
}

minios_main();
