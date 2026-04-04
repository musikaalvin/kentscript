:: Test Phase 6 - Serialization

print("Test: JSON");
let json_str = '{"name": "test", "value": 42}';
let parsed = system_json_loads(json_str);
if parsed['name'] == "test" {
    print("✓ json.loads() works");
}
let dumped = system_json_dumps({"key": "value"});
if dumped != none {
    print("✓ json.dumps() works");
}

print("\nTest: CSV");
system_file_write_text("/tmp/test.csv", "name,age\nAlice,30\nBob,25");
let csv_data = system_csv_reader("/tmp/test.csv");
if len(csv_data) == 3 {
    print("✓ csv.reader() works - " + str(len(csv_data)) + " rows");
}
system_file_remove("/tmp/test.csv");

print("\nTest: Pickle");
let data = {"test": [1, 2, 3]};
let pickled = system_pickle_dumps(data);
let unpickled = system_pickle_loads(pickled);
if unpickled['test'][0] == 1 {
    print("✓ pickle works");
}

print("\nTest: YAML");
let yaml_str = "key: value\nnumber: 42";
let yaml_parsed = system_yaml_load(yaml_str);
if yaml_parsed != none and yaml_parsed['key'] == "value" {
    print("✓ yaml works");
}

print("\n=== Phase 6 Serialization Complete ===");
