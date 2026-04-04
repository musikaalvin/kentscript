::Write to file
import os;

os.write_file("/tmp/test.txt", "Hello KentScript!");

:: Read from file
let content = os.read_file("/tmp/test.txt");
print(content);

:: Check if exists
if (os.exists("/tmp/test.txt")) {
    print("File exists!");
}

:: Append to file
os.append_file("/tmp/test.txt", " More content!");

:: Read again
let content2 = os.read_file("/tmp/test.txt");
print(content2);

:: Delete
os.remove("/tmp/test.txt");
print("File deleted!");
