:: KentScript file: system.ks
import os;

:: KentScript syntax, Python power!
let files = os.listdir("/");          :: Calls Python's os.listdir()
let cwd = os.getcwd();                :: Python's os.getcwd()
os.mkdir("new_folder");               :: Python's os.mkdir()

:: Your IMPROVEMENT: Add KentScript-only features!
func safe_delete(path) {
    try {
        os.remove(path);
        print("Deleted:", path);
    } except error {
        print("Cannot delete:", path, "Error:", error);
    }
}