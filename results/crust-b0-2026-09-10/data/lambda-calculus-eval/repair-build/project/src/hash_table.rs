use std::collections::HashMap;

use crate::common::AstNode;

pub struct HashTable {
    pub map: HashMap<String, AstNode>,
}

impl HashTable {
    pub fn new() -> Self {
        HashTable {
            map: HashMap::new(),
        }
    }

    pub fn insert(&mut self, key: String, value: AstNode) {
        self.map.insert(key, value);
    }

    pub fn get(&self, key: &str) -> Option<&AstNode> {
        self.map.get(key)
    }
}

impl Default for HashTable {
    fn default() -> Self {
        Self::new()
    }
}
