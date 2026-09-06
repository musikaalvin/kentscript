:: METHOD 1: Using the 'os' module (higher level)
import os;

:: Write to file
os.write_file("/tmp/msg.txt", "gotcha!");

:: Read from file
let content = os.read_file("/tmp/msg.txt");
print(content);

:: Get file info
if (os.path_exists("/tmp/msg.txt")) {
    print("File exists");
    print("Size: " + str(os.file_size("/tmp/msg.txt")));
}



:: Using file objects (similar to Python)
import os;

:: Open file for writing
let file = os.open_file("/tmp/msg.txt", "w");
file.write("gotcha!");
file.close();

:: Open file for reading
let file2 = os.open_file("/tmp/msg.txt", "r");
let content = file2.read_all();
print(content);
file2.close();



:: Using file objects (similar to Python)
import os;

:: Open file for writing
let file = os.open_file("/tmp/msg.txt", "w");
file.write("gotcha!");
file.close();

:: Open file for reading
let file2 = os.open_file("/tmp/msg.txt", "r");
let content = file2.read_all();
print(content);
file2.close();



:: Your language has these helpers built-in
import os;

:: Write file (simple)
os.write_file("/tmp/msg.txt", "gotcha!");

:: Read file (simple) 
let text = os.read_file("/tmp/msg.txt");
print(text);

:: Append to file
os.append_file("/tmp/msg.txt", "\nAnother line!");

:: Check if exists
if (os.exists("/tmp/msg.txt")) {
    print("File exists");
}

:: Delete file
os.remove("/tmp/msg.txt");
print("File deleted");
