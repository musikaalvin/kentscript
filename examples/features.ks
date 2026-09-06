:: KentScript v5.0 - Feature Showcase

:: 1. Type Checking
let name: string = "KentScript";
let version: float = 5.0;
let is_awesome: bool = true;

print("=== Type Checking ===");
print("Language:", name, version);

:: 2. List Comprehensions
let squares = [x ** 2 for x in range(10)];
print("\n=== List Comprehensions ===");
print("Squares:", squares);

let evens = [x for x in range(20) if x % 2 == 0];
print("Even numbers:", evens);

:: 3. Lambda Expressions
let double = (x) -> x * 2;
let add = (a, b) -> a + b;

print("\n=== Lambda Functions ===");
print("Double 5:", double(5));
print("Add 3 + 7:", add(3, 7));

:: 4. Pipe Operator
let data = [1, 2, 3, 4, 5];
let square_func = (lst) -> [x ** 2 for x in lst];
let sum_func = (lst) -> sum(lst);

let result = data | square_func | sum_func;
print("\n=== Pipe Operator ===");
print("Piped result:", result);

:: 5. Pattern Matching
let value = 2;
print("\n=== Pattern Matching ===");
match value {
    case 1: {
        print("Value is one");
    }
    case 2: {
        print("Value is two");
    }
    default: {
        print("Value is something else");
    }
}

:: 6. Ternary Operator
let age = 18;
let status = age >= 18 ? "Adult" : "Minor";
print("\n=== Ternary Operator ===");
print("Status:", status);

:: 7. Enhanced Assignment
let counter = 0;
counter += 5;
counter += 3;
print("\n=== Enhanced Assignment ===");
print("Counter:", counter);

:: 8. Const Variables
const PI = 3.14159;
print("\n=== Constants ===");
print("PI:", PI);

:: 9. Functions with Type Hints
func calculate(x: int, y: int) -> int {
    return x * y + x;
}

print("\n=== Type Hints in Functions ===");
print("Calculate:", calculate(5, 3));

:: 10. Classes and Objects
class Calculator {
    func add(a, b) {
        return a + b;
    }
    
    func multiply(a, b) {
        return a * b;
    }
}

let calc = Calculator();
print("\n=== Classes ===");
print("Calc add:", calc.add(10, 20));
print("Calc multiply:", calc.multiply(4, 5));

:: 11. Try-Except
print("\n=== Error Handling ===");
try {
    let unsafe_test = 10 / 0;
} except Exception as e {
    print("Caught error!");
}

:: 12. Dictionary Operations
let person = {"name": "Alice", "age": 30, "city": "NYC"};
print("\n=== Dictionaries ===");
print("Person:", person);
print("Name:", person["name"]);

:: 13. String Operations
let greeting = "Hello, " + name + "!";
print("\n=== Strings ===");
print(greeting);

print("\n=== All Features Tested Successfully! ===");
