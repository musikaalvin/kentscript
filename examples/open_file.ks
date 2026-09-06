:: A simple KentScript file program using fileio module
import fileio;

class File {
    func open(filename) {
        let content = fileio.read(filename, "utf-8");
        print(content);
        return ;
    }
}

let f = new File();
try {
    f.open("/home/pylord/Documents/apikeys.txt");
} except Exception as e {
    print("Error: " + str(e));
}
