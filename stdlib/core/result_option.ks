:: Result and Option types for error handling

enum Option<T> {
    Some(T),
    None
}

enum Result<T, E> {
    Ok(T),
    Err(E)
}

:: Option methods
func Option_is_some<T>(opt: Option<T>) -> bool {
    match opt {
        case Some(_) => return true;
        case None => return false;
    }
}

func Option_is_none<T>(opt: Option<T>) -> bool {
    match opt {
        case Some(_) => return false;
        case None => return true;
    }
}

func Option_unwrap<T>(opt: Option<T>) -> T {
    match opt {
        case Some(val) => return val;
        case None => {
            print("ERROR: Called unwrap() on None");
            unsafe { asm("ud2"); }
        }
    }
}

func Option_unwrap_or<T>(opt: Option<T>, default: T) -> T {
    match opt {
        case Some(val) => return val;
        case None => return default;
    }
}

:: Result methods
func Result_is_ok<T, E>(res: Result<T, E>) -> bool {
    match res {
        case Ok(_) => return true;
        case Err(_) => return false;
    }
}

func Result_is_err<T, E>(res: Result<T, E>) -> bool {
    match res {
        case Ok(_) => return false;
        case Err(_) => return true;
    }
}

func Result_unwrap<T, E>(res: Result<T, E>) -> T {
    match res {
        case Ok(val) => return val;
        case Err(e) => {
            print("ERROR: Called unwrap() on Err");
            unsafe { asm("ud2"); }
        }
    }
}

func Result_unwrap_or<T, E>(res: Result<T, E>, default: T) -> T {
    match res {
        case Ok(val) => return val;
        case Err(_) => return default;
    }
}

func Result_expect<T, E>(res: Result<T, E>, msg: str) -> T {
    match res {
        case Ok(val) => return val;
        case Err(_) => {
            print(msg);
            unsafe { asm("ud2"); }
        }
    }
}
