:: FILE I/O EXAMPLES
:: ═══════════════════════════════════════════════════════════════════════════

:: Example 1: File operations
func demo_file_io() {
    :: Write file
    File.write("test.txt", "Hello, KentScript!\n");
    File.append("test.txt", "Line 2\n");
    
    :: Read file
    let content = File.read("test.txt");
    print("File content:");
    print(content);
    
    :: List directory
    let files = File.ls(".");
    print("Directory listing:");
    for f in files {
        print(f);
    };
    
    :: File info
    print("File size: " + str(File.size("test.txt")) + " bytes");
};

:: Example 2: Create multiple files
func create_logs() {
    for i in range(3) {
        let filename = "log_" + str(i) + ".txt";
        File.write(filename, "Log entry " + str(i) + "\n");
    };
    print("Created 3 log files");
};

:: NETWORKING EXAMPLES
:: ═══════════════════════════════════════════════════════════════════════════

:: Example 3: Simple HTTP GET
func fetch_api() {
    try {
        let result = Net.http_get("https:::jsonplaceholder.typicode.com/posts/1");
        print("Status: " + str(result["status"]));
        print("Response: " + result["body"]);
    } except {
        print("Network error");
    };
};

:: Example 4: JSON operations
func fetch_json() {
    try {
        let data = Net.json_get("https:::jsonplaceholder.typicode.com/users/1");
        print("User data retrieved");
        print("Status: " + str(data["status"]));
    } except {
        print("Failed to fetch JSON");
    };
};

:: Example 5: POST request
func post_data() {
    let payload = {"name": "test", "value": 42};
    try {
        let result = Net.json_post("https:::jsonplaceholder.typicode.com/posts", payload);
        print("POST Status: " + str(result["status"]));
    } except {
        print("POST failed");
    };
};

:: SYSTEM COMMAND EXAMPLES
:: ═══════════════════════════════════════════════════════════════════════════

:: Example 6: Execute system commands
func system_commands() {
    :: Get current directory
    let cwd = Sys.cwd();
    print("Current directory: " + cwd);
    
    :: List files using ls (Unix/Linux/macOS) or dir (Windows)
    let result = Sys.exec("ls -la", true);
    if result["success"] {
        print("Command output:");
        print(result["stdout"]);
    } else {
        print("Command failed: " + result["stderr"]);
    };
};

:: Example 7: Environment variables
func env_example() {
    let path = Sys.env("PATH");
    print("PATH: " + path);
    
    :: Set environment variable
    Sys.set_env("MY_VAR", "test_value");
    print("Set MY_VAR");
};

:: Example 8: Change directory and list
func dir_operations() {
    let old_cwd = Sys.cwd();
    print("Old directory: " + old_cwd);
    
    :: Create and change to temp directory
    File.mkdir("temp_ks", true);
    Sys.chdir("temp_ks");
    
    print("New directory: " + Sys.cwd());
    
    :: Go back
    Sys.chdir(old_cwd);
    print("Back to: " + Sys.cwd());
};

:: THREADING EXAMPLES
:: ═══════════════════════════════════════════════════════════════════════════

:: Example 9: Basic threading
func counter(id, iterations) {
    for i in range(iterations) {
        print("Thread " + str(id) + ": " + str(i));
        sleep(0.1);
    };
    return id;
};

func thread_demo() {
    print("Starting threads...");
    
    :: Create threads
    let t1 = Thread(counter, (1, 3));
    let t2 = Thread(counter, (2, 3));
    let t3 = Thread(counter, (3, 3));
    
    :: Start them
    t1.start();
    t2.start();
    t3.start();
    
    :: Wait for completion
    let r1 = t1.join();
    let r2 = t2.join();
    let r3 = t3.join();
    
    print("All threads done");
    print("Results: " + str(r1) + " " + str(r2) + " " + str(r3));
};

:: Example 10: Thread pool
func process_item(item) {
    print("Processing: " + str(item));
    sleep(0.2);
    return item * 2;
};

func thread_pool_demo() {
    let pool = ThreadPool(4);
    
    :: Submit tasks
    let ids = [];
    for i in range(10) {
        let id = pool.submit(process_item, (i,));
        ids = ids + [id];
    };
    
    :: Get results
    let results = [];
    for id in ids {
        let result = pool.get_result(id, 5);
        results = results + [result];
        print("Result: " + str(result));
    };
    
    pool.shutdown();
    print("Pool completed");
};

:: Example 11: Mutex for thread safety
func shared_counter() {
    let mutex = Mutex();
    let count = 0;
    
    func increment() {
        mutex.acquire();
        count = count + 1;
        mutex.release();
        return count;
    };
    
    return increment;
};

:: MEMORY OPERATIONS
:: ═══════════════════════════════════════════════════════════════════════════

:: Example 12: Pointer operations
func memory_demo() {
    :: Allocate memory
    let ptr = Pointer.malloc(256);
    print("Allocated: " + str(ptr));
    
    :: Write string
    ptr.write_string(0, "Hello, Memory!");
    
    :: Read string
    let msg = ptr.read_string(0);
    print("Read: " + msg);
    
    :: Write byte
    ptr.write_byte(6, 87);  :: 'W'
    let b = ptr.read_byte(6);
    print("Byte at offset 6: " + str(b));
    
    :: Memory stats
    let stats = Pointer.memory_stats();
    print("Memory stats: " + str(stats));
    
    :: Free
    Pointer.free(ptr);
};

:: COMBINED EXAMPLE
:: ═══════════════════════════════════════════════════════════════════════════

:: Example 13: Complete workflow
func complete_example() {
    print("=== KentScript Production Example ===");
    
    :: Step 1: Create data file
    print("\n[1] Creating data file...");
    let data = "Line 1\nLine 2\nLine 3\n";
    File.write("data.txt", data);
    print("Created data.txt");
    
    :: Step 2: Read and process
    print("\n[2] Reading and processing...");
    let content = File.read("data.txt");
    let lines = content;
    print("Read " + str(len(lines)) + " characters");
    
    :: Step 3: Get current time via system
    print("\n[3] System time...");
    let current_time = time();
    print("Current timestamp: " + str(current_time));
    
    :: Step 4: Run background task
    print("\n[4] Running background task...");
    let task = Thread(counter, (999, 2));
    task.start();
    
    :: Step 5: Clean up
    print("\n[5] Cleanup...");
    task.join();
    File.delete("data.txt");
    print("Deleted data.txt");
    
    print("\n=== Example Complete ===");
};

:: MAIN EXECUTION
print("KentScript v8.0 Production - Example Program");
print("Uncomment the demo you want to run:");
print("  demo_file_io()");
print("  thread_pool_demo()");
print("  complete_example()");

:: Run one example
complete_example();
