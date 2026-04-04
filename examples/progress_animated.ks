import sys;
import time;
import color;

print(color.cyan("=== Animated Progress Bar Demo ==="));
print("");

:: Simple animated progress bar
print(color.yellow("Loading..."));
for i in range(0, 101) {
    let bar = color.progress_bar(i, 40, "green");
    sys.stdout.write("\r" + bar);
    sys.stdout.flush();
    time.sleep(0.03);
}
print(color.green(" Done!"));
print("");

:: Cyber style animation
print(color.yellow("Processing..."));
for i in range(0, 101) {
    let bar = color.progress_bar_cyber(i, 30, "cyan");
    sys.stdout.write("\r" + bar);
    sys.stdout.flush();
    time.sleep(0.02);
}
print(color.green(" Complete!"));
print("");

:: Matrix style animation
print(color.yellow("Hacking..."));
for i in range(0, 101) {
    let bar = color.progress_bar_matrix(i, 25);
    sys.stdout.write("\r" + bar);
    sys.stdout.flush();
    time.sleep(0.025);
}
print(color.green(" Access Granted!"));
