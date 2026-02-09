# KentScript FULL - Working Examples

## Example 1: Hello World
```kentscript
print("Hello, KentScript!");
```

## Example 2: Variables and Arithmetic
```kentscript
let x = 10;
let y = 20;
print(x + y);
print(x * y);
print(y / x);
```

## Example 3: Lists
```kentscript
let numbers = [1, 2, 3, 4, 5];
print(numbers);
print(len(numbers));
```

## Example 4: For Loop
```kentscript
for i in range(5) {
    print(i);
}
```

## Example 5: While Loop
```kentscript
let i = 0;
while i < 5 {
    print(i);
    i = i + 1;
}
```

## Example 6: If-Else Statement
```kentscript
let age = 25;
if age < 18 {
    print("Minor");
} elif age < 65 {
    print("Adult");
} else {
    print("Senior");
}
```

## Example 7: Functions
```kentscript
func add(a, b) {
    return a + b;
}

func fibonacci(n) {
    if n <= 1 {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

print(add(5, 3));
print(fibonacci(10));
```

## Example 8: Simple Class
```kentscript
class Dog {
    func __init__(name) {
        self.name = name;
    }
    
    func bark() {
        print(self.name);
    }
}

let dog = new Dog("Buddy");
dog.bark();
```

## Example 9: Calculator Class
```kentscript
class Calculator {
    func add(a, b) {
        return a + b;
    }
    
    func subtract(a, b) {
        return a - b;
    }
    
    func multiply(a, b) {
        return a * b;
    }
    
    func divide(a, b) {
        if b == 0 {
            return "Error: Division by zero";
        }
        return a / b;
    }
}

let calc = new Calculator();
print(calc.add(10, 5));
print(calc.multiply(4, 7));
print(calc.divide(20, 4));
```

## Example 10: List Comprehension
```kentscript
let numbers = [1, 2, 3, 4, 5];
let doubled = [x * 2 for x in numbers];
print(doubled);

let evens = [x for x in range(10) if x % 2 == 0];
print(evens);
```

## Example 11: FizzBuzz
```kentscript
for i in range(1, 16) {
    if i % 15 == 0 {
        print("FizzBuzz");
    } elif i % 3 == 0 {
        print("Fizz");
    } elif i % 5 == 0 {
        print("Buzz");
    } else {
        print(i);
    }
}
```

## Example 12: Dictionary
```kentscript
let person = {"name": "Alice", "age": 30, "city": "NYC"};
print(person["name"]);
print(person["age"]);
```

## Example 13: Try-Except
```kentscript
try {
    let result = 10 / 0;
} except ZeroDivisionError {
    print("Cannot divide by zero");
}
```

## Example 14: File Operations
```kentscript
import "file" as f;

f.write("test.txt", "Hello, KentScript!");
let content = f.read("test.txt");
print(content);

f.delete("test.txt");
```

## Example 15: Math Module
```kentscript
import "math" as m;

print(m.pi);
print(m.sqrt(16));
print(m.sin(0));
```

## Example 16: JSON Module
```kentscript
import "json" as j;

let data = {"name": "Alice", "age": 30};
let json_str = j.dumps(data);
print(json_str);
```

## Example 17: Pattern Matching
```kentscript
match 5 {
    case 1 {
        print("One");
    }
    case 5 {
        print("Five");
    }
    case _ {
        print("Other");
    }
}
```

## Example 18: Person Class with Methods
```kentscript
class Person {
    func __init__(name, age) {
        self.name = name;
        self.age = age;
    }
    
    func greet() {
        return self.name;
    }
    
    func birthday() {
        self.age = self.age + 1;
    }
}

let p = new Person("Alice", 25);
print(p.greet());
p.birthday();
print(p.age);
```

## Example 19: Recursion - Factorial
```kentscript
func factorial(n) {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}

print(factorial(5));
print(factorial(10));
```

## Example 20: Advanced Calculator with Memory
```kentscript
class AdvancedCalculator {
    func __init__() {
        self.memory = 0;
    }
    
    func add(a, b) {
        self.memory = a + b;
        return self.memory;
    }
    
    func multiply(a, b) {
        self.memory = a * b;
        return self.memory;
    }
    
    func get_memory() {
        return self.memory;
    }
    
    func clear_memory() {
        self.memory = 0;
    }
}

let calc = new AdvancedCalculator();
print(calc.add(10, 5));
print(calc.multiply(3, 4));
print(calc.get_memory());
calc.clear_memory();
print(calc.get_memory());
```
