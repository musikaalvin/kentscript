:: ============================================================================
:: KENTSCRIPT v6.0 - COMPREHENSIVE EXAMPLES
:: ============================================================================

:: ============================================================================
:: 1. VARIABLES AND BASIC SYNTAX (STRICT)
:: ============================================================================

let x = 5;
let y = 10.5;
let name = "John";
let active = true;

print("Variables:");
print(x);
print(name);


:: ============================================================================
:: 2. LISTS, SLICING, INDEXING
:: ============================================================================

let numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

:: Indexing
print("First element:");
print(numbers[0]);

:: Negative indexing
print("Last element:");
print(numbers[-1]);

:: Slicing
print("Slice [1:4]:");
print(numbers[1:4]);

print("Slice [::2] (every 2nd):");
print(numbers[::2]);

print("Slice [:5]:");
print(numbers[:5]);

print("Slice [5:]:");
print(numbers[5:]);

:: List operations
numbers.append(11);
print("After append:");
print(numbers);

let popped = numbers.pop();
print("Popped value:");
print(popped);


:: ============================================================================
:: 3. DICTIONARIES
:: ============================================================================

let person = {
    "name": "John",
    "age": 30,
    "email": "john@example.com"
};

print("Dictionary:");
print(person);

print("Name:");
print(person["name"]);

print("Age:");
print(person["age"]);


:: ============================================================================
:: 4. FUNCTIONS (STRICT SYNTAX)
:: ============================================================================

func add(a, b) {
    return a + b;
};

func greet(name) {
    print("Hello, " + name + "!");
};

print("Addition:");
print(add(5, 3));

greet("Alice");


:: ============================================================================
:: 5. LAMBDA EXPRESSIONS (FIXED)
:: ============================================================================

:: Correct lambda syntax: lambda params -> expression;
let square = lambda x -> x * x;
print("Lambda test (5^2):");
print(square(5));

let multiply = lambda x, y -> x * y;
print("Multiply 3 * 4:");
print(multiply(3, 4));

let add_lambda = lambda a, b -> a + b;
print("Add 7 + 8:");
print(add_lambda(7, 8));


:: ============================================================================
:: 6. CONTROL FLOW
:: ============================================================================

print("Control Flow:");

if (x > 3) {
    print("x is greater than 3");
} else {
    print("x is not greater than 3");
};

:: If-elif-else
let score = 85;
if (score >= 90) {
    print("Grade: A");
} else if (score >= 80) {
    print("Grade: B");
} else if (score >= 70) {
    print("Grade: C");
} else {
    print("Grade: F");
};


:: ============================================================================
:: 7. LOOPS
:: ============================================================================

print("For loop:");
for i in range(5) {
    print(i);
};

print("While loop:");
let counter = 0;
while (counter < 3) {
    print(counter);
    counter = counter + 1;
};

:: List iteration
print("Loop through list:");
let colors = ["red", "green", "blue"];
for color in colors {
    print(color);
};


:: ============================================================================
:: 8. MATH MODULE
:: ============================================================================

let math = math;

print("Math module:");
print("PI =");
print(math.pi);

print("sqrt(16) =");
print(math.sqrt(16));

print("sin(0) =");
print(math.sin(0));

print("factorial(5) =");
print(math.factorial(5));


:: ============================================================================
:: 9. STRING OPERATIONS
:: ============================================================================

let str = "KentScript";

print("String operations:");
print("Length:");
print(len(str));

print("Upper:");
print(str.upper());

print("Lower:");
print(str.lower());

let words = "hello world test".split(" ");
print("Split:");
print(words);


:: ============================================================================
:: 10. RANDOM MODULE
:: ============================================================================

let random = random;

print("Random number (0-1):");
print(random.random());

print("Random int (1-100):");
print(random.randint(1, 100));

let items = [1, 2, 3, 4, 5];
print("Random choice:");
print(random.choice(items));


:: ============================================================================
:: 11. JSON MODULE
:: ============================================================================

let json = json;

let data = {
    "name": "John",
    "age": 30
};

print("JSON stringify:");
let json_str = json.dumps(data);
print(json_str);

print("JSON parse:");
let parsed = json.loads(json_str);
print(parsed);


:: ============================================================================
:: 12. OS MODULE (File Operations)
:: ============================================================================

import os;

print("Current working directory:");
print(os.getcwd());

print("List current directory:");
let files = os.listdir(".");
print(files);


:: ============================================================================
:: 13. CLASSES
:: ============================================================================

class Animal {
    func __init__(name) {
        this.name = name;
    }
    
    func speak() {
        print(this.name + " makes a sound");
    }
}

class Dog extends Animal {
    func speak() {
        print(this.name + " barks!");
    }
}

let dog = new Dog("Buddy");
dog.speak();


:: ============================================================================
:: 14. TRY-CATCH
:: ============================================================================

try {
    let result = 10 / 0;
} catch (error) {
    print("Caught error: Division by zero");
};


:: ============================================================================
:: 15. MATCH STATEMENT (Pattern Matching)
:: ============================================================================

let value = 2;
match (value) {
    case 1: {
        print("One");
    }
    case 2: {
        print("Two");
    }
    case 3: {
        print("Three");
    }
    default: {
        print("Other");
    }
};


:: ============================================================================
:: 16. ARRAY/LIST COMPREHENSION STYLE
:: ============================================================================

let squared = [];
for i in range(5) {
    squared.append(i * i);
};
print("Squared numbers:");
print(squared);


:: ============================================================================
:: 17. FILTERING
:: ============================================================================

let numbers_to_filter = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
let evens = [];
for num in numbers_to_filter {
    if (num % 2 == 0) {
        evens.append(num);
    };
};
print("Even numbers:");
print(evens);


:: ============================================================================
:: 18. MULTIPLE RETURN VALUES (AS LIST)
:: ============================================================================

func get_coordinates() {
    return [10, 20];
};

let coords = get_coordinates();
print("Coordinates:");
print(coords[0], coords[1]);


:: ============================================================================
:: 19. DEFAULT PARAMETERS
:: ============================================================================

func greet_with_greeting(name, greeting) {
    if (greeting == null) {
        greeting = "Hello";
    };
    print(greeting + ", " + name + "!");
};

greet_with_greeting("Alice", "Hi");
greet_with_greeting("Bob", null);


:: ============================================================================
:: 20. HIGHER-ORDER FUNCTIONS
:: ============================================================================

func apply_operation(a, b, operation) {
    return operation(a, b);
};

let add_op = lambda x, y -> x + y;
let mult_op = lambda x, y -> x * y;

print("Apply add:");
print(apply_operation(5, 3, add_op));

print("Apply multiply:");
print(apply_operation(5, 3, mult_op));


:: ============================================================================
:: 21. TIME MODULE
:: ============================================================================

let time = time;

print("Current time:");
print(time.time());

let now = time.localtime();
print("Local time structure:");
print(now);


:: ============================================================================
:: 22. NESTED DATA STRUCTURES
:: ============================================================================

let matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
];

print("Matrix[0][1]:");
print(matrix[0][1]);

print("Full matrix:");
print(matrix);


:: ============================================================================
:: 23. RECURSIVE FUNCTIONS
:: ============================================================================

func factorial_func(n) {
    if (n <= 1) {
        return 1;
    };
    return n * factorial_func(n - 1);
};

print("Factorial of 5:");
print(factorial_func(5));

func fibonacci(n) {
    if (n <= 1) {
        return n;
    };
    return fibonacci(n - 1) + fibonacci(n - 2);
};

print("Fibonacci of 6:");
print(fibonacci(6));


:: ============================================================================
:: 24. CLOSURES
:: ============================================================================

func make_counter() {
    let count = 0;
    func increment() {
        count = count + 1;
        return count;
    };
    return increment;
};

let counter = make_counter();
print("Counter:");
print(counter());
print(counter());
print(counter());


:: ============================================================================
:: 25. BREAK AND CONTINUE
:: ============================================================================

print("Break example:");
for i in range(10) {
    if (i == 5) {
        break;
    };
    print(i);
};

print("Continue example:");
for i in range(5) {
    if (i == 2) {
        continue;
    };
    print(i);
};
