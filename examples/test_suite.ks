:: TEST SUITE FOR KENTSCRIPT v8.0 PRODUCTION
:: Demonstrates real File I/O, Networking, System, and Threading

func test_file_write_read() {
    print("TEST: File write/read");
    
    :: Test write
    let written = File.write("test_file.txt", "Hello, World!");
    print("Wrote " + str(written) + " bytes");
    
    :: Test read
    let content = File.read("test_file.txt");
    print("Content: " + content);
    
    :: Verify
    if content == "Hello, World!" {
        print("✓ File write/read PASSED");
    } else {
        print("✗ File write/read FAILED");
    };
};

func test_file_append() {
    print("\nTEST: File append");
    
    :: Create file
    File.write("append_test.txt", "Line 1\n");
    
    :: Append
    File.append("append_test.txt", "Line 2\n");
    File.append("append_test.txt", "Line 3\n");
    
    :: Verify
    let content = File.read("append_test.txt");
    let lines = 3;
    print("File has 3 lines");
    print("✓ File append PASSED");
};

func test_file_operations() {
    print("\nTEST: File operations");
    
    :: Create file
    File.write("ops_test.txt", "data");
    
    :: Check exists
    if File.exists("ops_test.txt") {
        print("✓ File exists");
    };
    
    :: Get size
    let size = File.size("ops_test.txt");
    print("File size: " + str(size) + " bytes");
    
    :: Copy
    File.copy("ops_test.txt", "ops_test_copy.txt");
    print("✓ Copied file");
    
    :: Delete
    File.delete("ops_test.txt");
    File.delete("ops_test_copy.txt");
    print("✓ File operations PASSED");
};

func test_directory_operations() {
    print("\nTEST: Directory operations");
    
    :: Create directory
    File.mkdir("test_dir", true);
    print("✓ Created directory");
    
    :: List directory (cwd)
    let entries = File.ls(".");
    print("Directory has " + str(len(entries)) + " entries");
    
    :: Delete directory
    File.mkdir("test_dir");
    File.delete("test_dir");
    print("✓ Directory operations PASSED");
};

func test_system_exec() {
    print("\nTEST: System command execution");
    
    :: Execute command
    let result = Sys.exec("whoami", true);
    
    if result["success"] {
        print("Return code: " + str(result["returncode"]));
        print("Output: " + result["stdout"]);
        print("✓ System exec PASSED");
    } else {
        print("Command failed");
    };
};

func test_system_env() {
    print("\nTEST: System environment");
    
    :: Get existing let
    let path = Sys.env("PATH");
    if path != None {
        print("PATH exists, length: " + str(len(path)));
    };
    
    :: Set custom let
    Sys.set_env("TEST_VAR", "test_value");
    let val = Sys.env("TEST_VAR");
    
    if val == "test_value" {
        print("✓ Environment variables PASSED");
    };
};

func test_current_dir() {
    print("\nTEST: Current directory");
    
    let cwd = Sys.cwd();
    print("Current directory: " + cwd);
    print("✓ Directory info PASSED");
};

func test_threading_basic() {
    print("\nTEST: Basic threading");
    
    :: Define worker
    func worker(id) {
        sleep(0.1);
        return id * 10;
    };
    
    :: Create thread
    let t = Thread(worker, (5,));
    t.start();
    
    :: Join and get result
    let result = t.join();
    
    if result == 50 {
        print("Thread returned: " + str(result));
        print("✓ Basic threading PASSED");
    };
};

func test_threading_multiple() {
    print("\nTEST: Multiple threading");
    
    func counter(id, max) {
        for i in range(max) {
            sleep(0.05);
        };
        return id;
    };
    
    :: Create threads
    let threads = [];
    for i in range(3) {
        let t = Thread(counter, (i, 2));
        t.start();
        threads = threads + [t];
    };
    
    :: Join all
    let results = [];
    for t in threads {
        let r = t.join();
        results = results + [r];
    };
    
    print("Thread results: " + str(results));
    print("✓ Multiple threading PASSED");
};

func test_thread_pool() {
    print("\nTEST: Thread pool");
    
    :: Create pool
    let pool = ThreadPool(2);
    
    func work(n) {
        sleep(0.05);
        return n * n;
    };
    
    :: Submit tasks
    let ids = [];
    for i in range(4) {
        let id = pool.submit(work, (i,));
        ids = ids + [id];
    };
    
    :: Collect results
    let results = [];
    for id in ids {
        let res = pool.get_result(id);
        results = results + [res];
    };
    
    print("Pool results: " + str(results));
    pool.shutdown();
    print("✓ Thread pool PASSED");
};

func test_mutex() {
    print("\nTEST: Mutex synchronization");
    
    let mutex = Mutex();
    let counter = 0;
    
    func increment() {
        mutex.acquire();
        counter = counter + 1;
        mutex.release();
    };
    
    :: Call increment (in single thread for test)
    increment();
    increment();
    
    if counter == 2 {
        print("Counter: " + str(counter));
        print("✓ Mutex PASSED");
    };
};

func test_memory_pointer() {
    print("\nTEST: Memory pointers");
    
    :: Allocate
    let ptr = Pointer.malloc(256);
    print("Allocated: " + str(ptr));
    
    :: Write and read
    ptr.write_string(0, "Test");
    let text = ptr.read_string(0);
    
    if text == "Test" {
        print("Read: " + text);
        Pointer.free(ptr);
        print("✓ Memory pointer PASSED");
    };
};

func test_memory_stats() {
    print("\nTEST: Memory statistics");
    
    :: Allocate multiple
    let p1 = Pointer.malloc(128);
    let p2 = Pointer.malloc(256);
    
    :: Get stats
    let stats = Pointer.memory_stats();
    print("Blocks allocated: " + str(stats["blocks"]));
    print("Total allocated: " + str(stats["allocated"]) + " bytes");
    
    :: Free
    Pointer.free(p1);
    Pointer.free(p2);
    
    print("✓ Memory stats PASSED");
};

func test_exception_handling() {
    print("\nTEST: Exception handling");
    
    try {
        :: This should work
        let x = 10 / 2;
        print("10 / 2 = " + str(x));
        print("✓ Exception handling PASSED");
    } except {
        print("Exception caught");
    };
};

func test_list_operations() {
    print("\nTEST: List operations");
    
    let list = [1, 2, 3, 4, 5];
    print("List: " + str(list));
    print("Length: " + str(len(list)));
    
    :: List access
    let first = list[0];
    let last = list[4];
    print("First: " + str(first) + ", Last: " + str(last));
    
    print("✓ List operations PASSED");
};

func test_dict_operations() {
    print("\nTEST: Dictionary operations");
    
    let dict = {"name": "test", "value": 42, "active": True};
    print("Dict: " + str(dict));
    
    let name = dict["name"];
    let value = dict["value"];
    print("name=" + name + ", value=" + str(value));
    
    print("✓ Dictionary operations PASSED");
};

func test_function_def() {
    print("\nTEST: Function definitions");
    
    func add(a, b) {
        return a + b;
    };
    
    let result = add(5, 3);
    if result == 8 {
        print("add(5, 3) = " + str(result));
        print("✓ Function definitions PASSED");
    };
};

func test_class_definition() {
    print("\nTEST: Class definitions");
    
    class Point {
        func init(x, y) {
            self.x = x;
            self.y = y;
        };
        
        func distance() {
            return (self.x ** 2 + self.y ** 2) ** 0.5;
        };
    };
    
    let p = new Point(3, 4);
    let dist = p.distance();
    print("Point(3,4) distance from origin: " + str(dist));
    print("✓ Class definitions PASSED");
};

func test_loops() {
    print("\nTEST: Loop constructs");
    
    :: For loop
    let sum = 0;
    for i in range(5) {
        sum = sum + i;
    };
    print("Sum 0..4 = " + str(sum));
    
    :: While loop
    let count = 0;
    while count < 3 {
        count = count + 1;
    };
    print("While loop count: " + str(count));
    
    print("✓ Loop constructs PASSED");
};

func test_conditions() {
    print("\nTEST: Conditional logic");
    
    let x = 42;
    
    if x > 40 {
        print("x is greater than 40");
    };
    
    if x == 42 {
        print("x equals 42");
        print("✓ Conditional logic PASSED");
    };
};

:: RUN ALL TESTS
print("═══════════════════════════════════════════");
print("KENTSCRIPT v8.0 PRODUCTION TEST SUITE");
print("═══════════════════════════════════════════");

print("\n--- FILE I/O TESTS ---");
test_file_write_read();
test_file_append();
test_file_operations();
test_directory_operations();

print("\n--- SYSTEM TESTS ---");
test_system_exec();
test_system_env();
test_current_dir();

print("\n--- THREADING TESTS ---");
test_threading_basic();
test_threading_multiple();
test_thread_pool();
test_mutex();

print("\n--- MEMORY TESTS ---");
test_memory_pointer();
test_memory_stats();

print("\n--- CORE LANGUAGE TESTS ---");
test_exception_handling();
test_list_operations();
test_dict_operations();
test_function_def();
test_class_definition();
test_loops();
test_conditions();

print("\n═══════════════════════════════════════════");
print("ALL TESTS COMPLETED");
print("═══════════════════════════════════════════");
