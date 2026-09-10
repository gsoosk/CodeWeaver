use crate::common;
use std::collections::HashMap;
pub const HASH_TABLE_SIZE: usize = 2000;
pub struct HashTable {
table: HashMap<String, common::AstNode>,
}
impl HashTable {
    pub fn new() -> Self {
        HashTable {
            table: HashMap::new(),
        }
    }
    pub fn insert(&mut self, key: &str, value: common::AstNode) {
        self.table.insert(key.to_string(), value);
    }
    pub fn table_exists(&self, key: &str) -> bool {
        self.table.contains_key(key)
    }
    pub fn search(&self, key: &str) -> Option<&common::AstNode> {
        match self.table.get(key) {
            Some(value) => {
                if is_default_sentinel(value) {
                    None
                } else {
                    Some(value)
                }
            }
            None => None,
        }
    }
    pub fn delete(&mut self, key: &str) {
        self.table.remove(key);
    }
}

fn is_default_sentinel(value: &common::AstNode) -> bool {
    if value.type_ != common::AstNodeType::VAR {
        return false;
    }
    match &value.node {
        common::AstNodeUnion::Variable(v) => v.name.is_empty() && v.type_.is_empty(),
        _ => false,
    }
}

pub fn hash(key: &str) -> u32 {
    let mut hash_val: u64 = 5381;
    for c in key.bytes() {
        hash_val = hash_val
            .wrapping_shl(5)
            .wrapping_add(hash_val)
            .wrapping_add(c as u64);
    }
    (hash_val % HASH_TABLE_SIZE as u64) as u32
}
pub fn createHashTable() -> HashTable {
    HashTable::new()
}
pub fn destroyHashTable(_hashTable: HashTable) {
    // HashMap's Drop already frees everything; nothing more to do.
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixture-based: no mocks, direct in-memory HashTable state (per analysis.md).

    #[test]
    fn test_insert_then_search_returns_value() {
        let mut table = HashTable::new();
        let value = common::AstNode {
            type_: common::AstNodeType::VAR,
            node: common::AstNodeUnion::Variable(common::Variable {
                name: "x".to_string(),
                type_: "Bool".to_string(),
            }),
        };
        table.insert("x", value);
        let found = table.search("x").expect("expected value");
        assert_eq!(common::ast_to_string(found), "(x : Bool) ");
    }

    #[test]
    fn test_search_returns_none_for_default_sentinel_value() {
        let mut table = HashTable::new();
        table.insert("x", common::AstNode::default());
        assert!(table.search("x").is_none());
    }

    #[test]
    fn test_table_exists_reflects_key_presence() {
        let mut table = HashTable::new();
        assert!(!table.table_exists("x"));
        table.insert("x", common::AstNode::default());
        assert!(table.table_exists("x"));
    }

    #[test]
    fn test_delete_then_search_returns_none() {
        let mut table = HashTable::new();
        let value = common::AstNode {
            type_: common::AstNodeType::VAR,
            node: common::AstNodeUnion::Variable(common::Variable {
                name: "x".to_string(),
                type_: String::new(),
            }),
        };
        table.insert("x", value);
        assert!(table.search("x").is_some());
        table.delete("x");
        assert!(table.search("x").is_none());
    }

    #[test]
    fn test_hash_is_deterministic_and_bounded() {
        let h1 = hash("some_key");
        let h2 = hash("some_key");
        assert_eq!(h1, h2);
        assert!((h1 as usize) < HASH_TABLE_SIZE);
    }
}