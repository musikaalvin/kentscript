:: Module System Test

import math;
import random;
import json;
import time;

print("=== Built-in Modules Test ===");

:: Math module
print("\nMath Module:");
print("Pi:", math.pi);
print("Sqrt(16):", math.sqrt(16));
print("Sin(0):", math.sin(0));

:: Random module
print("\nRandom Module:");
print("Random:", random.random());
print("Randint(1-10):", random.randint(1, 10));

:: JSON module
print("\nJSON Module:");
let data = {"name": "John", "age": 30};
let json_str = json.dumps(data);
print("JSON string:", json_str);
let parsed = json.loads(json_str);
print("Parsed:", parsed);

:: Time module
print("\nTime Module:");
print("Current time:", time.time());

print("\n=== All Modules Working! ===");
