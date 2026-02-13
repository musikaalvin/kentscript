KentScript - Modern Scripting Language 🚀

TypeScript syntax meets Python power - A clean, expressive language for the modern developer

<p align="center">
  <img src="https://img.shields.io/badge/Version-5.0-blue?style=for-the-badge" alt="Version 5.0">
Script is a modern, expressive scripting language that combines the familiar syntax of TypeScript/JavaScript with the power and ecosystem of Python. Designed for productivity and readability, it brings web development syntax to system scripting, data science, automation, and beyond.

✨ Why KentScript?

· For Web Developers: Use familiar TypeScript/JavaScript syntax for system tasks
· For Python Users: Get modern syntax while keeping Python's ecosystem
· For Everyone: Clean, readable code with powerful features out of the box

📅 Project Details

Detail Information
Creator pyLord (Anonymous Developer)
Created 01/February/2026
First Release v1.0 - 10/February/2026
Current Version v5.0 (Alpha)
Repository https://github.com/musikaalvin/kentscript
Written In Python 3.8+
License MIT License
Status Active Development

🧬 Language DNA

KentScript is a curated blend of the best modern languages:

Language Influence Features
TypeScript/JavaScript 70% Syntax, type system, modern features
Python 15% Runtime, standard library, REPL
Rust 5% Safety ambitions, concurrency model
Kotlin/Swift 5% Modern syntax sugar, expressiveness
C#/Java 3% OOP system, class structure
Ruby 2% Expressiveness, DSL capabilities

🚀 Features

✅ Implemented Features

· Modern Syntax: TypeScript-like syntax with type annotations
· Full Interpreter: Lexer, parser, AST, interpreter
· Type System: Runtime type checking with inference
· REPL: Interactive shell with syntax highlighting
· Standard Library: Access to Python's entire ecosystem
· Async/Await: Modern asynchronous programming
· Pattern Matching: Rust/Swift-style match expressions
· List Comprehensions: Python-style list generators
· Lambda Expressions: Anonymous functions
· Pipe Operator: Functional programming pipelines
· Package Manager: Simple package installation (KPM)
· AST Caching: Faster execution on subsequent runs

🚧 In Development (v6.0)

· Real Threading: Actual thread spawning and management
· Bytecode VM: Stack-based virtual machine for performance
· Garbage Collection: Custom memory management system
· Module System: Proper module isolation and namespacing
· GUI Toolkit: Native GUI framework based on tkinter

🚀 Quick Start

Installation

```bash
# Clone the repository
git clone https://github.com/musikaalvin/kentscript.git
cd kentscript

# Run directly (no installation needed!)
python kentscript.py

# Or make it executable
chmod +x kentscript.py
./kentscript.py
```

Hello World

Create hello.ks:

```typescript
// Traditional hello world
print("Hello, World!");

// With modern features
let greeting: string = "Hello, KentScript!";
print(greeting);
```

Run it:

```bash
python kentscript.py hello.ks
```

Interactive REPL

```bash
python kentscript.py
# Or
./kentscript.py
```

📚 Language Syntax

Variables and Types

```typescript
// Variable declaration with type inference
let name = "KentScript";              // Inferred as string
let version: float = 5.0;            // Explicit type annotation
const PI = 3.14159;                  // Constant

// Type system
let age: int = 25;
let price: float = 19.99;
let active: bool = true;
let data: list = [1, 2, 3];
let config: dict = {"key": "value"};
let nothing: None = None;

// Type-safe operations
let result: int = calculate();      // Type checking at runtime
```

Functions

```typescript
// Function definition
func greet(name: string) -> string {
    return "Hello, " + name + "!";
}

// Lambda functions
let square = func(x: int) -> int { return x * x; };

// Async functions
async func fetchData(url: string) -> dict {
    // Async operations
    return await http.get(url);
}

// Decorators
@log_execution
@validate_params
func process(data: list) -> list {
    return data.map(item => item * 2);
}
```

Control Flow

```typescript
// If-else statements
if temperature > 30 {
    print("It's hot!");
} elif temperature > 20 {
    print("It's warm");
} else {
    print("It's cold");
}

// Loops
while counter < 10 {
    print(counter);
    counter += 1;
}

for item in items {
    print(item);
}

for i in range(0, 10, 2) {
    print(i);
}

// Pattern matching
match status_code {
    case 200: print("Success");
    case 404: print("Not Found");
    case 500: print("Server Error");
    default: print("Unknown status");
}
```

Collections

```typescript
// Lists
let numbers: list = [1, 2, 3, 4, 5];
let matrix: list = [[1, 2], [3, 4]];

// List comprehensions
let squares = [x * x for x in range(10)];
let evens = [x for x in range(20) if x % 2 == 0];

// Dictionaries
let person: dict = {
    "name": "Alice",
    "age": 30,
    "active": true
};

// Sets (planned)
let unique: set = {1, 2, 3, 3, 4};  // Becomes {1, 2, 3, 4}
```

Classes and OOP

```typescript
// Class definition
class Person {
    func __init__(name: string, age: int) {
        self.name = name;
        self.age = age;
    }
    
    func greet() -> string {
        return "Hello, I'm " + self.name;
    }
    
    func have_birthday() {
        self.age += 1;
    }
}

// Instantiation
let alice = new Person("Alice", 30);
print(alice.greet());
alice.have_birthday();
```

Error Handling

```typescript
// Try-catch-finally
try {
    let data = read_file("config.json");
    let config = json.parse(data);
} except error {
    print("Error reading config:", error);
} finally {
    cleanup_resources();
}

// Custom exceptions
func validate_age(age: int) {
    if age < 0 {
        throw "Age cannot be negative";
    }
}
```

Functional Programming

```typescript
// Pipe operator
let result = data 
    | filter(x => x > 0) 
    | map(x => x * 2) 
    | reduce((a, b) => a + b, 0);

// Higher-order functions
let process = func(data: list, transform: function) -> list {
    return data.map(transform);
};

// Partial application
let add = func(a: int, b: int) -> int { return a + b; };
let addFive = add(5, _);  // Partial application
```

📦 Standard Library

KentScript provides access to Python's entire ecosystem through clean wrappers:

```typescript
// File I/O
import io;
let content = io.read_file("data.txt");
io.write_file("output.txt", "Hello");

// Mathematics
import math;
let root = math.sqrt(25);
let sine = math.sin(math.pi / 2);

// Networking
import http;
let response = http.get("https://api.example.com");
print(response.status, response.body);

// Date and Time
import datetime;
let now = datetime.now();
let tomorrow = now.add_days(1);

// Cryptography
import crypto;
let hash = crypto.sha256("secret");
let encoded = crypto.base64_encode("data");
```

🛠️ Package Manager (KPM)

KentScript includes a simple package manager:

```bash
# Install packages
python kentscript.py
>>> kpm install http-utils
>>> kpm install data-science https://raw.githubusercontent.com/example/ds.ks

# List installed packages
>>> kpm list

# Uninstall packages
>>> kpm uninstall http-utils
```

📁 Project Structure

```
kentscript/
├── kentscript.py          # Main interpreter
├── examples/              # Example programs
│   ├── hello.ks
│   ├── fibonacci.ks
│   ├── web_server.ks
│   └── data_processing.ks
├── ks_modules/            # Installed packages
├── .ks_cache/             # AST cache for faster execution
├── tests/                 # Test suite
├── docs/                  # Documentation
└── README.md              # This file
```

📊 Performance

Operation Speed Notes
Lexing ~100k LOC/sec Pure Python implementation
Parsing ~50k LOC/sec Recursive descent parser
Execution ~10k ops/sec Direct AST interpretation
With Cache ~30k ops/sec Cached AST re-execution
Bytecode ~100k ops/sec Planned (v6.0)

🎯 Use Cases

System Automation

```typescript
import os;
import datetime;

// Automated backup script
func backup_files(source: string, destination: string) {
    let timestamp = datetime.now().format("%Y%m%d_%H%M%S");
    let backup_dir = os.path.join(destination, "backup_" + timestamp);
    
    os.mkdir(backup_dir);
    let files = os.listdir(source);
    
    for file in files {
        let source_path = os.path.join(source, file);
        let dest_path = os.path.join(backup_dir, file);
        os.copy(source_path, dest_path);
    }
    
    print("Backup completed:", backup_dir);
}
```

Web Development

```typescript
import http;
import json;

// Simple API client
class APIClient {
    func __init__(base_url: string) {
        self.base_url = base_url;
    }
    
    async func get_users() -> list {
        let response = await http.get(self.base_url + "/users");
        return json.parse(response.body);
    }
    
    async func create_user(user_data: dict) -> dict {
        let response = await http.post(
            self.base_url + "/users",
            json.stringify(user_data)
        );
        return json.parse(response.body);
    }
}
```

Data Processing

```typescript
// Data pipeline
let raw_data = read_csv("data.csv");
let cleaned = raw_data
    | filter(row => row.valid)
    | map(row => {
        return {
            "id": row.id,
            "value": parse_float(row.value),
            "category": normalize_category(row.category)
        };
    })
    | group_by(row => row.category);

write_json("output.json", cleaned);
```

🛣️ Roadmap

v5.0 (Current) - Complete Interpreter

· ✅ Full lexer/parser implementation
· ✅ Type system with runtime checking
· ✅ REPL with syntax highlighting
· ✅ Standard library wrappers
· ✅ Package manager (basic)
· ✅ Error handling system

v6.0 (In Development) - Production Ready

· 🚧 Real threading implementation
· 🚧 Bytecode compiler and VM
· 🚧 Garbage collection system
· 🚧 Enhanced module system
· 🚧 GUI toolkit
· 🚧 Performance optimizations

v7.0 (Planned) - Advanced Features

· 📅 Borrow checker (Rust-inspired)
· 📅 Native compilation to machine code
· 📅 WebAssembly target
· 📅 Language Server Protocol (LSP)
· 📅 Debugger and profiler
· 📅 Package registry server

🤝 Contributing

KentScript is open to contributions! Here's how you can help:

1. Report Bugs: Open an issue with reproduction steps
2. Suggest Features: Share your ideas for improvement
3. Submit PRs: Fix bugs or implement features
4. Write Documentation: Improve docs or add examples
5. Create Packages: Build useful KentScript libraries

Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/kentscript.git
cd kentscript

# Run tests
python -m pytest tests/

# Create new feature branch
git checkout -b feature/awesome-feature

# Make changes and test
python kentscript.py examples/hello.ks

# Submit pull request
```

Code Style

· Follow PEP 8 for Python code
· Use type hints for all function signatures
· Add docstrings to public functions/classes
· Write tests for new features
· Keep KentScript syntax clean and consistent

📝 License

KentScript is released under the MIT License:

```
MIT License

Copyright (c) 2026-2027 pyLord

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

🙏 Acknowledgments

KentScript stands on the shoulders of giants:

· Python - For the runtime and massive ecosystem
· TypeScript - For inspiring the syntax and type system
· JavaScript/ECMAScript - For modern language features
· Rust - For safety and concurrency inspiration
· All Contributors - For making open source awesome

📞 Support

· GitHub Issues: https://github.com/musikaalvin/kentscript/issues
· Email: (Add your contact if desired)
· Discord/Community: (Add if you create one)

🌟 Star History

https://api.star-history.com/svg?repos=musikaalvin/kentscript&type=Date

---

<p align="center">
  Made with ❤️ by pyLord • 
  <a href="https://github.com/musikaalvin/kentscript">Star on GitHub</a> • 
  <a href="https://github.com/musikaalvin/kentscript/issues">Report Issue</a> • 
  <a href="https://github.com/musikaalvin/kentscript/pulls">Contribute</a>
</p>

<p align="center">
  <sub>"TypeScript syntax, Python power – the best of both worlds"</sub>
</p>

---

Quick Links: Syntax Cheatsheet • API Reference • Examples • Contributing Guide
