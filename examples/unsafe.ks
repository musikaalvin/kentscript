import hardware;
import syscall;

:: Configure serial port (COM1)
unsafe {
    :: Set baud rate (115200)
    hardware.outb(0x80, 0x3FB);     :: Set DLAB=1
    hardware.outb(0x01, 0x3F8);      :: Divisor latch low byte
    hardware.outb(0x00, 0x3F9);      :: Divisor latch high byte
    hardware.outb(0x03, 0x3FB);      :: 8 bits, no parity, 1 stop bit
    
    :: Enable FIFO
    hardware.outb(0xC7, 0x3FA);
    
    :: Send data
    hardware.outb(0x48, 0x3F8);      :: 'H'
    hardware.outb(0x65, 0x3F8);      :: 'e'
    hardware.outb(0x6C, 0x3F8);      :: 'l'
    hardware.outb(0x6C, 0x3F8);      :: 'l'
    hardware.outb(0x6F, 0x3F8);      :: 'o'
}