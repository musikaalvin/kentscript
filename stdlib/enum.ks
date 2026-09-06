:: enum.ks - Enum utilities
::
:: KentScript has native enum support:
::   enum Color { RED = 1, GREEN = 2, BLUE = 3 }
::   print(Color.RED);  -> 1
::
:: This module provides additional utilities:
::   import enum;
::   let Color = enum.Enum("Color", ["RED", "GREEN", "BLUE"]);

func Enum(name, fields) {
  let _ = {};
  let i = 0;
  for field in fields {
    _[field] = i;
    i = i + 1;
  }
  return _;
}

func names(enum_type) {
  let result = [];
  for key in enum_type {
    if typeof(key) == "str" {
      result.push(key);
    }
  }
  return result;
}

func values(enum_type) {
  let result = [];
  for key in enum_type {
    if typeof(key) == "str" {
      result.push(enum_type[key]);
    }
  }
  return result;
}

func has(enum_type, name) {
  for key in enum_type {
    if key == name { return true; }
  }
  return false;
}
