# KentScript - Complete Master Guide

## 🚀 Three Versions Included

### 1. **kentscript.py** (Original v2.0)
- Basic interpreter
- All roadmap features
- Good for learning

### 2. **kentscript_full.py** (Production v2.5) ⭐ RECOMMENDED
- ✅ **Full OOP support** with proper class/method handling
- ✅ **All examples working perfectly**
- ✅ **Clean architecture**
- ✅ **1,700+ lines of code**
- ✅ Production ready

### 3. **kentscript_advanced.py** (Professional v3.0)
- 🔧 **Debugger** with breakpoints
- 📊 **Profiler** for performance analysis
- 📝 **Static code analyzer**
- 💾 **Bytecode compilation**
- 🔍 **Memory introspection**
- 👨‍💻 **Advanced REPL**

---

## ⭐ Quick Start (2 minutes)

### Installation
```bash
pip install rich prompt_toolkit pygments
```

### Run Basic Version
```bash
python kentscript.py script.ks
python kentscript.py  # Interactive mode
```

### Run Full Version (Recommended)
```bash
python kentscript_full.py script.ks
python kentscript_full.py  # Interactive mode with proper syntax
```

### Run Advanced Version
```bash
python kentscript_advanced.py --advanced
python kentscript_advanced.py --debug script.ks
python kentscript_advanced.py --profile script.ks
```

---

## 📚 Language Features

### Variables and Constants
```kentscript
let x = 10;
const PI = 3.14159;
```

### All Data Types
```kentscript
let number = 42;
let decimal = 3.14;
let text = "Hello";
let flag = True;
let empty = None;
let items = [1, 2, 3];
let person = {"name": "Alice", "age": 30};
```

### Operators
```kentscript
# Arithmetic
x + 5
x - 3
x * 2
x / 2
x % 5
x ** 2

# Comparison
x == 5
x != 5
x > 5
x < 5
x >= 5
x <= 5

# Logical
a and b
a or b
not a
```

### Control Flow

**If-Elif-Else:**
```kentscript
if x > 0 {
    print("Positive");
} elif x < 0 {
    print("Negative");
} else {
    print("Zero");
}
```

**While Loop:**
```kentscript
while x < 10 {
    print(x);
    x = x + 1;
}
```

**For Loop:**
```kentscript
for i in range(5) {
    print(i);
}

for item in list {
    print(item);
}
```

**Match Statement:**
```kentscript
match x {
    case 1 {
        print("One");
    }
    case 2 {
        print("Two");
    }
    case _ {
        print("Other");
    }
}
```

### Functions

**Basic Function:**
```kentscript
func add(a, b) {
    return a + b;
}

print(add(3, 5));  # 8
```

**Recursive Function:**
```kentscript
func factorial(n) {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}

print(factorial(5));  # 120
```

### Classes (Full OOP)

**Simple Class:**
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

**Full Calculator Class:**
```kentscript
class Calculator {
    func __init__(name) {
        self.name = name;
        self.result = 0;
    }
    
    func add(a, b) {
        self.result = a + b;
        return self.result;
    }
    
    func multiply(a, b) {
        self.result = a * b;
        return self.result;
    }
    
    func get_result() {
        return self.result;
    }
}

let calc = new Calculator("MyCalc");
print(calc.add(5, 3));       # 8
print(calc.multiply(4, 7));  # 28
print(calc.get_result());    # 28
```

### List Comprehensions
```kentscript
let doubled = [x * 2 for x in range(5)];
print(doubled);  # [0, 2, 4, 6, 8]

let evens = [x for x in range(10) if x % 2 == 0];
print(evens);  # [0, 2, 4, 6, 8]
```

### Error Handling
```kentscript
try {
    let result = 10 / 0;
} except ZeroDivisionError {
    print("Cannot divide by zero");
} finally {
    print("Done");
}
```

### Module System

**Math Module:**
```kentscript
import "math" as m;

print(m.pi);       # 3.14159...
print(m.sqrt(16)); # 4.0
```

**File Module:**
```kentscript
import "file" as f;

f.write("test.txt", "Hello");
let content = f.read("test.txt");
print(content);

f.delete("test.txt");
```

**JSON Module:**
```kentscript
import "json" as j;

let data = {"name": "Alice", "age": 30};
let json_str = j.dumps(data);
print(json_str);
```

**Network Module:**
```kentscript
import "network" as net;

let response = net.http_get("https://example.com");
print(response);
```

**Regex Module:**
```kentscript
import "regex" as rx;

let has_digits = rx.search("\\d+", "abc123");
print(has_digits);  # True

let matches = rx.findall("\\d+", "a1b2c3");
print(matches);  # [1, 2, 3]
```

**Crypto Module:**
```kentscript
import "crypto" as c;

let hash = c.sha256("password");
print(hash);

let encoded = c.base64_encode("hello");
print(encoded);  # aGVsbG8=
```

---

## 🔥 20+ Working Examples

See **WORKING_EXAMPLES_FULL.md** for all examples including:

1. Hello World
2. Arithmetic
3. Lists
4. Loops
5. Conditionals
6. Functions
7. Classes
8. List Comprehensions
9. FizzBuzz
10. Dictionaries
11. Try-Except
12. File Operations
13. Math Module
14. JSON Operations
15. Pattern Matching
16. Person Class
17. Factorial
18. Advanced Calculator
19. Fibonacci
20. And more!

---

## 🛠️ Advanced Features (v3.0)

### Using the Debugger
```bash
python kentscript_advanced.py --debug script.ks
```

Commands in REPL:
```
breakpoint 10    - Set breakpoint at line 10
stack           - Show call stack
debug on/off    - Enable/disable debugger
```

### Performance Profiling
```bash
python kentscript_advanced.py --profile script.ks
```

Then in REPL:
```
profile on      - Start profiling
profile off     - Stop and show results
```

### Code Analysis
```ks
analyze code    - Analyze code for issues
stats          - Show compilation statistics
memory         - Show memory usage
```

---

## 📖 File Structure

```
/mnt/user-data/outputs/
├── kentscript.py               (v2.0 - Original)
├── kentscript_full.py          (v2.5 - Full OOP) ⭐
├── kentscript_advanced.py      (v3.0 - Professional)
├── QUICK_START.md
├── KENTSCRIPT_2.0_DOCUMENTATION.md
├── WORKING_EXAMPLES_FULL.md    (20+ examples)
├── README.md
├── SUMMARY.md
└── requirements.txt
```

---

## ✅ What's Fixed

### From Original v1.0 to v2.5
- ✅ Return statements in functions
- ✅ Class methods with proper `self` handling
- ✅ Attribute assignment (self.x = y)
- ✅ Member access (obj.member)
- ✅ List with multiple elements
- ✅ Proper error messages
- ✅ Complete OOP support
- ✅ All examples working

### v3.0 Additions
- ✅ Bytecode compilation
- ✅ Debugger with breakpoints
- ✅ Performance profiler
- ✅ Static analyzer
- ✅ Memory introspection
- ✅ Advanced REPL

---

## 🎯 Recommended Usage

### For Learning
Use **kentscript_full.py**:
```bash
python kentscript_full.py
```

### For Production Scripts
Use **kentscript_full.py**:
```bash
python kentscript_full.py myscript.ks
```

### For Development & Debugging
Use **kentscript_advanced.py**:
```bash
python kentscript_advanced.py --advanced
# Then use: breakpoint, debug, profile commands
```

### For Performance Analysis
Use **kentscript_advanced.py**:
```bash
python kentscript_advanced.py --profile myscript.ks
```

---

## 📝 Writing Scripts

Create a `.ks` file with proper syntax:

**hello.ks:**
```kentscript
print("Hello, KentScript!");
```

**calculator.ks:**
```kentscript
class Calculator {
    func add(a, b) {
        return a + b;
    }
    
    func multiply(a, b) {
        return a * b;
    }
}

let calc = new Calculator();
print(calc.add(5, 3));
print(calc.multiply(4, 7));
```

**fibonacci.ks:**
```kentscript
func fib(n) {
    if n <= 1 {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

for i in range(10) {
    print(fib(i));
}
```

---

## 🔌 Module Reference

### math
- `pi` - Pi constant
- `e` - Euler's number
- `sqrt(x)` - Square root
- `sin(x)` - Sine
- `cos(x)` - Cosine
- `tan(x)` - Tangent
- `log(x)` - Natural logarithm
- `floor(x)` - Floor
- `ceil(x)` - Ceiling

### file
- `read(path)` - Read file
- `write(path, content)` - Write file
- `append(path, content)` - Append to file
- `exists(path)` - Check if exists
- `delete(path)` - Delete file
- `read_json(path)` - Read JSON
- `write_json(path, data)` - Write JSON
- `read_csv(path)` - Read CSV
- `write_csv(path, data)` - Write CSV

### json
- `dumps(obj)` - Convert to string
- `loads(str)` - Parse string

### network
- `http_get(url)` - GET request
- `http_post(url, data)` - POST request

### regex
- `match(pattern, text)` - Check match
- `search(pattern, text)` - Search
- `findall(pattern, text)` - Find all
- `sub(pattern, repl, text)` - Replace

### crypto
- `md5(text)` - MD5 hash
- `sha256(text)` - SHA256 hash
- `base64_encode(text)` - Encode
- `base64_decode(text)` - Decode

### time
- `time()` - Current time
- `sleep(seconds)` - Sleep
- `datetime()` - Current datetime

---

## 🚨 Syntax Notes

### Important
- Use semicolons (`;`) to end statements
- Use braces (`{}`) for blocks
- Indentation is not required (but good practice)
- All keywords are lowercase

### Example (Correct Syntax)
```kentscript
func greet(name) {
    let message = "Hello, " + name;
    return message;
}

let result = greet("Alice");
print(result);
```

---

## 📊 Performance Tips

1. **Use list comprehensions** instead of loops
2. **Avoid deep recursion** (use iteration when possible)
3. **Profile your code** with v3.0: `python kentscript_advanced.py --profile`
4. **Minimize variable scope**
5. **Cache repeated calculations**

---

## 🐛 Troubleshooting

### "Syntax Error" on simple code
- Make sure to end statements with `;`
- Check that all `{` have matching `}`
- Use proper keyword names (lowercase)

### Classes not working
- Make sure to use `self.` for instance variables
- Use `new ClassName()` to instantiate
- Methods don't need parentheses when defined with `func`

### Module not found
- Use correct module names: `math`, `file`, `json`, `network`, `regex`, `crypto`
- Use correct import syntax: `import "module" as m;`

### Functions return None
- Check that you have `return` statement
- Return statement must be before function ends

---

## 🎓 Learning Path

1. **Start with:** `python kentscript_full.py` (REPL)
2. **Learn basics:** Variables, operators, control flow
3. **Try loops:** For, while, list comprehensions
4. **Learn functions:** Define and call functions
5. **Master classes:** OOP with `class` and `new`
6. **Use modules:** Import and use built-in modules
7. **Debug code:** Use `python kentscript_advanced.py --advanced`
8. **Profile:** Use profiler for optimization

---

## 📞 Support

- **Quick questions:** Check WORKING_EXAMPLES_FULL.md
- **Syntax help:** See syntax examples above
- **Modules:** Refer to module reference
- **Errors:** Check troubleshooting section

---

## Version History

- **v2.0** - Original with all roadmap features
- **v2.5** - Production-grade, all OOP working, 20+ examples
- **v3.0** - Advanced: debugger, profiler, analyzer

---

**Happy Coding! 🚀**

*KentScript - Where beautiful code meets power*
