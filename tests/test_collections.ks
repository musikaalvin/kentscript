:: Test Phase 4 - Collections

print("Test: collections.deque()");
let d = system_collections_deque([1, 2, 3]);
if d != none {
    print("✓ collections.deque() works");
}

print("\nTest: collections.counter()");
let c = system_collections_counter(["a", "b", "a"]);
if c != none {
    print("✓ collections.counter() works");
}

print("\nTest: collections.ordered_dict()");
let od = system_collections_ordered_dict();
if od != none {
    print("✓ collections.ordered_dict() works");
}

print("\nTest: collections.defaultdict()");
let dd = system_collections_defaultdict(list);
if dd != none {
    print("✓ collections.defaultdict() works");
}

print("\nTest: collections.namedtuple()");
let Point = system_collections_namedtuple("Point", ["x", "y"]);
if Point != none {
    print("✓ collections.namedtuple() works");
}

print("\n=== Phase 4 Collections Complete ===");
