:: testing - Unit testing framework

class TestCase {
    func __init__(self) {
        self.passed = 0;
        self.failed = 0;
        self.errors = [];
    }
    
    func assert_equal(self, actual, expected, msg) {
        if actual == expected {
            self.passed = self.passed + 1;
        } else {
            self.failed = self.failed + 1;
            let error = msg != none ? msg : f"Expected {expected}, got {actual}";
            self.errors.push(error);
            print(f"FAIL: {error}");
        }
    }
    
    func assert_not_equal(self, actual, expected, msg) {
        if actual != expected {
            self.passed = self.passed + 1;
        } else {
            self.failed = self.failed + 1;
            let error = msg != none ? msg : f"Expected not {expected}";
            self.errors.push(error);
            print(f"FAIL: {error}");
        }
    }
    
    func assert_true(self, value, msg) {
        self.assert_equal(value, true, msg);
    }
    
    func assert_false(self, value, msg) {
        self.assert_equal(value, false, msg);
    }
    
    func assert_none(self, value, msg) {
        self.assert_equal(value, none, msg);
    }
    
    func assert_not_none(self, value, msg) {
        self.assert_not_equal(value, none, msg);
    }
    
    func assert_in(self, item, container, msg) {
        if container.indexOf(item) != -1 {
            self.passed = self.passed + 1;
        } else {
            self.failed = self.failed + 1;
            let error = msg != none ? msg : f"{item} not in {container}";
            self.errors.push(error);
            print(f"FAIL: {error}");
        }
    }
    
    func assert_raises(self, exception_type, fn, msg) {
        try {
            fn();
            self.failed = self.failed + 1;
            let error = msg != none ? msg : f"Expected {exception_type} to be raised";
            self.errors.push(error);
            print(f"FAIL: {error}");
        } except e {
            self.passed = self.passed + 1;
        }
    }
    
    func run(self) {
        print(f"\nRunning tests...");
        print(f"Passed: {self.passed}");
        print(f"Failed: {self.failed}");
        return self.failed == 0;
    }
}

func test(name, fn) {
    print(f"\nTest: {name}");
    try {
        fn();
        print("  PASS");
        return true;
    } except e {
        print(f"  FAIL: {e}");
        return false;
    }
}

func assert_equal(actual, expected, msg) {
    if actual != expected {
        let error = msg != none ? msg : f"Expected {expected}, got {actual}";
        raise error;
    }
}

func assert_true(value, msg) {
    assert_equal(value, true, msg);
}

func assert_false(value, msg) {
    assert_equal(value, false, msg);
}

export {
    TestCase, test, assert_equal, assert_true, assert_false
};
