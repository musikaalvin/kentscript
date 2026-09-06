unsafe {
    let vga = 0xB8000 as ptr;
    let msg = "Hello";
    for i in range(5) {
        *vga = (msg[i] as int) | (0x0F << 8);
        vga = vga + 2;
    };
};
