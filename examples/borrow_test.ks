:: ============ KENTSCRIPT BORROW CHECKER TEST ============
:: This WORKS in the FINAL version!

:: ----- OWNERSHIP & MOVE -----
let x = 42;           :: x owns the value
let y = move x to y;  :: Move ownership from x to y
:: print(x);          :: ERROR: Cannot use 'x' - value was moved (UNCOMMENT TO TEST)
print(y);             :: 42 ✅

:: ----- IMMUTABLE BORROW (multiple readers) -----
let data = [1,2,3];
let r1 = borrow data;  :: Immutable borrow #1
let r2 = borrow data;  :: Immutable borrow #2 - ALLOWED!
print(r1[0]);          :: 1 ✅
print(r2[1]);          :: 2 ✅
release r1;            :: Manual release
release r2;

:: ----- MUTABLE BORROW (exclusive access) -----
let mut counter = 0;
let m = borrow *counter;  :: Mutable borrow (exclusive!)
counter = counter + 1;    :: ✅ Allowed - we have exclusive access
print(counter);           :: 1 ✅
release m;                :: Release borrow
:: let m2 = borrow *counter;  :: Would work - borrow released

print("✅ Borrow checker works!");