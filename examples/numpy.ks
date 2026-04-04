:: KentScript user sees:
import numpy as np;

let array = np.array([1, 2, 3]);  :: KentScript syntax
let result = array * 2;           :: Calls numpy operations

:: Behind scenes: KentScript → Python objects → numpy C code
print (result);