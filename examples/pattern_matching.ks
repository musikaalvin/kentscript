:: Pattern Matching in KentScript
:: Works correctly - prints directly from match cases

func describe_number(n) {
    match n {
        case 0: {
            print("Zero");
        }
        case 1: {
            print("One");
        }
        case 2: {
            print("Two");
        }
        default: {
            print("Other: " + str(n));
        }
    }
}

:: Test pattern matching
describe_number(0);
describe_number(1);
describe_number(2);
describe_number(42);

print("");

func describe_status(code) {
    match code {
        case 200: {
            print("200: OK");
        }
        case 404: {
            print("404: Not Found");
        }
        case 500: {
            print("500: Internal Server Error");
        }
        default: {
            print("Unknown status code");
        }
    }
}

print("HTTP Status Codes:");
describe_status(200);
describe_status(404);
describe_status(500);
describe_status(418);

print("");
print("Pattern matching working!");
