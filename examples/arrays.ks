:: ═══════════════════════════════════════════════════════════════════
:: KentScript Array Showcase
:: ═══════════════════════════════════════════════════════════════════

:: ── Array Creation ────────────────────────────────────────
print("=== Array Creation ===");

:: Empty array
let empty = [];
print("Empty: " + json.stringify(empty));

:: Array with initial values
let numbers = [1, 2, 3, 4, 5];
print("Numbers: " + json.stringify(numbers));

:: Array with mixed types
let mixed = [1, "hello", true, 3.14];
print("Mixed: " + json.stringify(mixed));

:: Array of strings
let names = ["Alice", "Bob", "Charlie"];
print("Names: " + json.stringify(names));

:: ── Array Properties ──────────────────────────────────────────
print("\n=== Array Properties ===");
print("Length: " + numbers.length);
print("First element: " + numbers[0]);
print("Last element: " + numbers[numbers.length - 1]);

:: ── Array Methods ────────────────────────────────────────────
print("\n=== Array Methods ===");

:: push - add element to end
let arr = [1, 2];
arr.push(3);
arr.push(4);
arr.push(5);
print("After push(3,4,5): " + json.stringify(arr));

:: pop - remove and return last element
let popped = arr.pop();
print("Popped: " + popped);
print("After pop: " + json.stringify(arr));

:: unshift - add element to beginning
arr.unshift(0);
print("After unshift(0): " + json.stringify(arr));

:: shift - remove and return first element
let shifted = arr.shift();
print("Shifted: " + shifted);
print("After shift: " + json.stringify(arr));

:: ── Array Iteration ───────────────────────────────────────────
print("\n=== Array Iteration ===");

:: Using for-in-range
for i in range(numbers.length) {
    print("  [" + i + "] = " + numbers[i]);
}

:: ── Array Slicing ─────────────────────────────────────────────
print("\n=== Array Slicing ===");
let slice = [1, 2, 3, 4, 5];
print("Original: " + json.stringify(slice));

:: Note: KentScript supports basic indexing
print("Element at index 2: " + slice[2]);

:: ── Array Searching ─────────────────────────────────────────
print("\n=== Array Searching ===");
let fruits = ["apple", "banana", "cherry", "banana"];

:: contains - check if element exists
print("Contains apple: " + fruits.contains("apple"));
print("Contains mango: " + fruits.contains("mango"));

:: indexOf - find element index
:: Note: using iteration to find index
let found = false;
for i in range(fruits.length) {
    if fruits[i] == "banana" {
        print("Found banana at index: " + i);
        found = true;
    }
}

:: ── Array Modification ─────────────────────────��────────────
print("\n=== Array Modification ===");
let nums = [1, 2, 3, 4, 5];

:: Reverse the array manually
let reversed = [];
for i in range(nums.length) {
    reversed.push(nums[nums.length - 1 - i]);
}
print("Reversed: " + json.stringify(reversed));

:: ── Array with Structs ────────────────────────────────────────
print("\n=== Array with Structs ===");
class Point {
    let x = 0;
    let y = 0;
    
    func new(x, y) {
        self.x = x;
        self.y = y;
    }
    
    func to_string() {
        return "Point(" + self.x + "," + self.y + ")";
    }
}

let points = [Point(1, 2), Point(3, 4), Point(5, 6)];
for i in range(points.length) {
    print("  " + points[i].to_string());
}

:: ── Array Copy ─────────────────────────────────────────────
print("\n=== Array Copy ===");
let original = [1, 2, 3];
let copy = original;
copy.push(4);
print("Original: " + json.stringify(original));
print("Copy (same reference): " + json.stringify(copy));

:: ── Array Filtering Concept ───────────────────────────────────
print("\n=== Array Filtering (manual) ===");
let all_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
let evens = [];
let odds = [];

for i in range(all_numbers.length) {
    if all_numbers[i] % 2 == 0 {
        evens.push(all_numbers[i]);
    } else {
        odds.push(all_numbers[i]);
    }
}
print("Evens: " + json.stringify(evens));
print("Odds: " + json.stringify(odds));

:: ═══════════════════════════════════════════════════════════════════
print("\n=== All Tests Complete ===");