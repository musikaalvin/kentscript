:: Test Object-Oriented Programming

print("Test: Classes");
class Point {
    func __init__(self, x, y) {
        self.x = x;
        self.y = y;
    }
    
    func distance(self) {
        return self.x + self.y;
    }
}

let p = Point(3, 4);
if p != none {
    print("✓ class instantiation works");
}

print("\n=== OOP Complete ===");
