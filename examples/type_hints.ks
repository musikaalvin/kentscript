:: example_type_hints.ks
:: Demonstrates optional type hints

:: Function with type hints
func add(a: int, b: int) -> int {
    return a + b;
}

:: Function with type hints
func multiply(x: float, y: float) -> float {
    return x * y;
}

:: Variables with type hints
let name: string = "KentScript";
let version: int = 4;
let pi: float = 3.14159;

print("Addition: ", add(5, 3));
print("Multiplication: ", multiply(2.5, 4.0));

print("\nTyped variables:");
print("Name: ", name);
print("Version: ", version);
print("Pi: ", pi);

:: Function with complex types
func greet(name: string) -> string {
    return "Hello, " + name;
}

print("\n", greet("World"));

print("\n✓ Type hints working! (documentation only in v4.0)");
