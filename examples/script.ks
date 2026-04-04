:: Variable declaration with type hint
let x: int = 10;

:: Function definition
func add(a: int, b: int) -> int {
    return a + b;
}

:: Threading
thread heavyComputation(data);

:: List comprehension
let squares = [n * n for n in range(10)];

:: Pattern matching
match value {
    case 1: print("One");
    case 2: print("Two");
    default: print("Other");
}

:: Pipe operator
let result = data | filter | map | reduce;