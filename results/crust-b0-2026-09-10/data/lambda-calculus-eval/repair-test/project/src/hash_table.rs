// A small generic hash table implementation, keyed by string, used to
// represent variable/environment bindings.

use std::collections::HashMap;

#[derive(Debug, Clone, Default)]
pub struct HashTable<V> {
    pub map: HashMap<String, V>,
}

impl<V> HashTable<V> {
    pub fn new() -> Self {
        HashTable {
            map: HashMap::new(),
        }
    }
}

/// Insert `key` -> `value` into `table`. Overwrites any existing value.
pub fn insert<V>(table: &mut HashTable<V>, key: &str, value: V) {
    table.map.insert(key.to_string(), value);
}

/// Look up `key` in `table`, returning a clone of the value if present.
pub fn search<V: Clone>(table: &HashTable<V>, key: &str) -> Option<V> {
    table.map.get(key).cloned()
}

/// Return true if `key` exists in `table`.
pub fn table_exists<V>(table: &HashTable<V>, key: &str) -> bool {
    table.map.contains_key(key)
}
