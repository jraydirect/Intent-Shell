//! Entity extraction from user input

use crate::types::Entity;
use std::collections::HashMap;
use regex::Regex;

/// Extract entities from user input
///
/// Identifies paths, files, numbers, and other structured data.
pub struct EntityExtractor {
    patterns: Vec<(Regex, String)>, // (pattern, entity_type)
}

impl EntityExtractor {
    pub fn new() -> Self {
        // Compile regex patterns once - these should never fail
        // Note: Rust regex doesn't support lookahead/lookbehind, so we filter after matching
        let patterns = vec![
            // Quoted paths/files
            (Regex::new(r#""([^"]+)""#).expect("Invalid regex pattern"), "path".to_string()),
            (Regex::new(r"'([^']+)'").expect("Invalid regex pattern"), "path".to_string()),
            // Environment variables
            (Regex::new(r"%([A-Z_]+)%").expect("Invalid regex pattern"), "envvar".to_string()),
            // File extensions
            (Regex::new(r"\b(\w+\.(txt|pdf|doc|docx|jpg|png|log|json|xml|py|exe))\b").expect("Invalid regex pattern"), "file".to_string()),
            // Numbers with units (must come before plain numbers)
            (Regex::new(r"\b(\d+)\s*(gb|mb|kb|percent|%)").expect("Invalid regex pattern"), "number_with_unit".to_string()),
            // Plain numbers
            (Regex::new(r"\b(\d+)\b").expect("Invalid regex pattern"), "number".to_string()),
        ];
        
        Self { patterns }
    }
    
    pub fn extract(&self, text: &str) -> Vec<Entity> {
        let mut entities = Vec::new();
        let text_lower = text.to_lowercase();
        
        // Check for special path references
        let special_paths: HashMap<&str, &str> = [
            ("desktop", "Desktop"),
            ("downloads", "Downloads"),
            ("documents", "Documents"),
            ("temp", "TEMP"),
            ("appdata", "APPDATA"),
            ("userprofile", "USERPROFILE"),
            ("home", "HOME"),
        ]
        .iter()
        .cloned()
        .collect();
        
        for (path_name, _) in &special_paths {
            if let Some(start) = text_lower.find(path_name) {
                entities.push(Entity::new(
                    "special_path".to_string(),
                    path_name.to_string(),
                    path_name.to_string(),
                    start,
                    start + path_name.len(),
                ));
            }
        }
        
        // Extract using regex patterns
        // Track positions of number_with_unit matches to avoid duplicates
        let mut number_with_unit_positions = std::collections::HashSet::new();
        
        for (pattern, entity_type) in &self.patterns {
            for cap in pattern.captures_iter(text) {
                if let Some(matched) = cap.get(0) {
                    let start = matched.start();
                    let end = matched.end();
                    
                    // If this is a number_with_unit, track its position
                    if entity_type == "number_with_unit" {
                        number_with_unit_positions.insert(start);
                        // Convert to regular "number" type for consistency
                        let value = cap.get(1).map(|m| m.as_str()).unwrap_or("");
                        entities.push(Entity::new(
                            "number".to_string(),
                            value.to_string(),
                            matched.as_str().to_string(),
                            start,
                            end,
                        ));
                    } else if entity_type == "number" {
                        // Skip plain numbers that overlap with number_with_unit
                        if !number_with_unit_positions.contains(&start) {
                            let value = cap.get(1).map(|m| m.as_str()).unwrap_or("");
                            entities.push(Entity::new(
                                entity_type.clone(),
                                value.to_string(),
                                matched.as_str().to_string(),
                                start,
                                end,
                            ));
                        }
                    } else {
                        let value = cap.get(1).map(|m| m.as_str()).unwrap_or("");
                        entities.push(Entity::new(
                            entity_type.clone(),
                            value.to_string(),
                            matched.as_str().to_string(),
                            start,
                            end,
                        ));
                    }
                }
            }
        }
        
        entities
    }
}

impl Default for EntityExtractor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_extract_number() {
        let extractor = EntityExtractor::new();
        let entities = extractor.extract("list 5 processes");
        
        assert!(!entities.is_empty());
        assert!(entities.iter().any(|e| e.entity_type == "number" && e.value == "5"));
    }
    
    #[test]
    fn test_extract_path() {
        let extractor = EntityExtractor::new();
        let entities = extractor.extract(r#"open "C:\Users\Desktop""#);
        
        assert!(!entities.is_empty());
        assert!(entities.iter().any(|e| e.entity_type == "path"));
    }
}
