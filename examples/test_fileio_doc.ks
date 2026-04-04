import fileio;
import path;
fileio.write("/tmp/test_doc2.txt", "Hello world", "utf-8");
print(fileio.read("/tmp/test_doc2.txt", "utf-8"));
print(path.getsize("/tmp/test_doc2.txt"));
let f = fileio.open("/tmp/test_doc2.txt", "rb");
let data = f.read();
print(data);
f.close();