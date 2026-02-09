# 🚀 KentScript 2.0 - Quick Start Guide

## Installation (2 minutes)

### 1. Install Dependencies

```bash
pip install rich prompt_toolkit pygments
```

### 2. Run KentScript

**Interactive mode (REPL):**
```bash
python kentscript.py
```

**Run a script:**
```bash
python kentscript.py script.ks
```

---

## 5-Minute Tutorial

### Lesson 1: Hello World

Create `hello.ks`:
```kentscript
print("Hello, KentScript!")
```

Run it:
```bash
python kentscript.py hello.ks
```

### Lesson 2: Variables and Basic Operations

Create `math.ks`:
```kentscript
let x = 10
let y = 20

print(x + y)      # 30
print(x * y)      # 200
print(y / x)      # 2.0
print(y % 3)      # 2
print(x ** 2)     # 100
```

### Lesson 3: Lists and Loops

Create `loops.ks`:
```kentscript
let numbers = [1, 2, 3, 4, 5]

for num in numbers {
    print(num)
}

# List comprehension
let doubled = [x * 2 for x in numbers]
print(doubled)  # [2, 4, 6, 8, 10]
```

### Lesson 4: Functions

Create `functions.ks`:
```kentscript
func greet(name) {
    return "Hello, " + name + "!"
}

print(greet("Alice"))
print(greet("Bob"))

# Fibonacci
func fib(n) {
    if n <= 1 {
        return n
    }
    return fib(n - 1) + fib(n - 2)
}

print(fib(7))  # 13
```

### Lesson 5: Classes

Create `classes.ks`:
```kentscript
class Dog {
    func __init__(name) {
        self.name = name
    }
    
    func bark() {
        print(self.name + " says Woof!")
    }
}

let dog = new Dog("Buddy")
dog.bark()  # Buddy says Woof!
```

### Lesson 6: File Operations

Create `files.ks`:
```kentscript
import "file" as f

# Write
f.write("hello.txt", "Hello, KentScript!")

# Read
let content = f.read("hello.txt")
print(content)

# JSON
let data = {"name": "Alice", "age": 30}
f.write_json("data.json", data)

let loaded = f.read_json("data.json")
print(loaded["name"])
```

### Lesson 7: Pattern Matching

Create `regex.ks`:
```kentscript
import "regex" as rx

let text = "Hello 123 World"

# Find numbers
let has_numbers = rx.search("\\d+", text)
print(has_numbers)  # True

# Find all
let numbers = rx.findall("\\d+", "a1b2c3")
print(numbers)  # ["1", "2", "3"]
```

### Lesson 8: Error Handling

Create `errors.ks`:
```kentscript
func safe_divide(a, b) {
    try {
        return a / b
    } except ZeroDivisionError as e {
        return "Error!"
    }
}

print(safe_divide(10, 2))  # 5.0
print(safe_divide(10, 0))  # Error!
```

---

## REPL Interactive Mode

```bash
python kentscript.py
```

Then try these commands:

```
>>> let x = 5
>>> let y = 10
>>> print(x + y)
15

>>> vars
Variables:
  x: 5
  y: 10

>>> help
Commands:
  exit, quit, q  - Exit REPL
  help           - Show this help
  vars           - Show all variables
  funcs          - Show all functions
  clear          - Clear screen
```

---

## Cheat Sheet

### Variables
```kentscript
let name = "Alice"        # Variable
const PI = 3.14159        # Constant
```

### Types
```kentscript
let num = 42              # Integer
let decimal = 3.14        # Float
let text = "hello"        # String
let flag = True           # Boolean
let items = [1, 2, 3]     # List
let data = {"a": 1}       # Dictionary
```

### Operators
```kentscript
x + y          # Addition
x - y          # Subtraction
x * y          # Multiplication
x / y          # Division
x % y          # Modulo
x ** y         # Power
x == y         # Equal
x != y         # Not equal
x > y          # Greater than
x < y          # Less than
x and y        # Logical AND
x or y         # Logical OR
not x          # Logical NOT
```

### Control Flow
```kentscript
if condition {
    # code
} elif other {
    # code
} else {
    # code
}

while condition {
    # code
}

for item in list {
    # code
}

match value {
    case 1 { }
    case 2 { }
    case _ { }
}
```

### Functions
```kentscript
func name(param1, param2) {
    return result
}
```

### Classes
```kentscript
class ClassName {
    func __init__(param) {
        self.prop = param
    }
    
    func method() {
        # code
    }
}

let obj = new ClassName(value)
```

### Built-in Functions
```kentscript
print(x)        # Print
len(list)       # Length
type(x)         # Type
int(x)          # Convert to int
str(x)          # Convert to string
sorted(list)    # Sort
max(list)       # Maximum
min(list)       # Minimum
sum(list)       # Sum
```

### Modules
```kentscript
import "math" as m        # Math operations
import "file" as f        # File I/O
import "network" as net   # HTTP requests
import "regex" as rx      # Pattern matching
import "crypto" as c      # Hashing, encoding
import "json" as j        # JSON parsing
import "time" as t        # Time operations
```

---

## Common Mistakes to Avoid

❌ **Wrong:** Forgetting quotes for strings
```kentscript
let name = Alice        # Error!
```
✅ **Correct:**
```kentscript
let name = "Alice"      # OK
```

❌ **Wrong:** Missing braces
```kentscript
if x > 5
    print(x)            # Error!
```
✅ **Correct:**
```kentscript
if x > 5 {
    print(x)            # OK
}
```

❌ **Wrong:** Dividing by zero
```kentscript
let result = 10 / 0     # ZeroDivisionError!
```
✅ **Correct:**
```kentscript
try {
    let result = 10 / 0
} except ZeroDivisionError as e {
    print("Error!")
}
```

❌ **Wrong:** Using undefined variables
```kentscript
print(name)             # NameError!
```
✅ **Correct:**
```kentscript
let name = "Alice"
print(name)             # OK
```

---

## Useful Patterns

### Safe File Reading
```kentscript
import "file" as f

try {
    let data = f.read("config.json")
} except Exception as e {
    print("Failed to read config")
}
```

### List Filtering
```kentscript
let numbers = [1, 2, 3, 4, 5]
let evens = [x for x in numbers if x % 2 == 0]
```

### Error Handling
```kentscript
try {
    # dangerous operation
} except Exception as e {
    print("Error: " + str(e))
} finally {
    # cleanup
}
```

### Iterating with Index
```kentscript
let items = ["a", "b", "c"]
for i in range(len(items)) {
    print(i)          # 0, 1, 2
    print(items[i])   # a, b, c
}
```

### String Building
```kentscript
let first = "Hello"
let second = "World"
let message = first + ", " + second + "!"
```

---

## Next Steps

1. **Read the full documentation:** `KENTSCRIPT_2.0_DOCUMENTATION.md`
2. **Try the examples:** `EXAMPLES.md`
3. **Experiment in REPL:** `python kentscript.py`
4. **Build projects:** Create `.ks` files and run them

---

## Troubleshooting

**Issue:** "Command not found: python"
- **Solution:** Use `python3` or add Python to PATH

**Issue:** "Module not found" error
- **Solution:** Install dependencies: `pip install rich prompt_toolkit pygments`

**Issue:** Syntax errors
- **Solution:** Check matching braces and quotes. Use REPL to debug incrementally.

**Issue:** Variable not found
- **Solution:** Make sure you declared it with `let`. KentScript is case-sensitive.

---

## Getting Help

- Type `help` in the REPL
- Read the full documentation
- Check EXAMPLES.md for code samples
- Ensure all parentheses and braces match

---

**Happy Coding! 🎉**

