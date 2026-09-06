:: KentScript Bare-Metal Kernel

func serial_write(msg: str) {
    let i = 0;
    while i < msg.len() {
        print(msg[i]);
        i = i + 1;
    }
};

func main() {
    serial_write("KentScript Bare-Metal Kernel\n");
    serial_write("Running in Ring 0\n");
    serial_write("Ready!\n");
};
