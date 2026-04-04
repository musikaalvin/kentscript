:: example_list_comprehensions.ks
:: Demonstrates list comprehensions feature

:: Basic list comprehension
let squares = [x * x for x in range(10)];
print("Squares: ", squares);

:: List comprehension with condition
let even_squares = [x * x for x in range(10) if x % 2 == 0];
print("Even squares: ", even_squares);

:: Nested comprehension (numbers divisible by 3)
let div_by_three = [n for n in range(1, 30) if n % 3 == 0];
print("Divisible by 3: ", div_by_three);

:: String manipulation
let words = ["hello", "world", "kentscript"];
let upper_words = [w for w in words];  
print("Words: ", upper_words);

:: Mathematical transformations
let powers = [2 ** i for i in range(8)];
print("Powers of 2: ", powers);

print("\n✓ List comprehensions working!");
