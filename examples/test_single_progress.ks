import sys;
import time;
import color;

print(color.cyan("Testing single progress bar..."));

for i in range(0, 101) {
    let bar = color.progress_bar(i, 30, "green");
    sys.stdout.write("\r" + bar);
    sys.stdout.flush();
    time.sleep(0.02);
}

print(color.green(" Done!"));
