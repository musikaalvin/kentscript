:: dataclass.ks - Python-like dataclass utilities
::
:: Usage:
::   import dataclass;
::   let Point = dataclass.make("Point", ["x", "y"], [0, 0]);
::   let p = Point();
::   p["x"] = 10; p["y"] = 20;
::   print(p["x"]);

func make(name, field_names, defaults) {
  let _fields = [];
  let i = 0;
  for fn in field_names {
    let d = i < len(defaults) ? defaults[i] : none;
    let f = {};
    f["name"] = fn;
    f["val"] = d;
    _fields.push(f);
    i = i + 1;
  }

  let constructor = func() {
    let obj = {};
    for f in _fields {
      obj[f["name"]] = f["val"];
    }
    return obj;
  };

  return constructor;
}
