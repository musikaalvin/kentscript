import time;
let t1 = time.time();
for i in range(0,1000){
 print(i);
}
let t2 = time.time();
let elapsed = t2 - t1;
let ms = elapsed * 1000.0;
if (ms >= 1000.0) {
    let secs = ms / 1000.0;
    print("Completed in ");
    print(secs);
    print(" s (");
    print(ms);
    print(" ms)");
} else {
    print("Completed in ");
    print(ms);
    print(" ms");
}
