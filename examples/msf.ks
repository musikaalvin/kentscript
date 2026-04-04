:: KentScript version of a Metasploit-like module selector

class ExploitManager {
    func init() {
        self.current_module = none;
        self.options = {};
    }

    func use(module_path) {
        self.current_module = module_path;
        print("Selected module: " + module_path);
    }

    func set(key, value) {
        self.options[key] = value;
        print(key + " => " + value);
    }

    func run() {
        if (self.current_module == none) {
            print("Error: No module selected.");
        } else {
            print("Launching exploit: " + self.current_module);
        };
    }
}

msf = new ExploitManager();
msf.use("exploit/multi/handler");
msf.set("LHOST", "192.168.1.10");
msf.run();
