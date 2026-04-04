print("KentScript Full Test");

File.write("test_out.txt", "Hello KentScript");
let x = File.read("test_out.txt");
print(x);

let cwd = Sys.cwd();
print(cwd);

print("Done");
