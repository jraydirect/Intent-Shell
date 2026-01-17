//! Core data types for parser results

use serde::{Deserialize, Serialize};

/// Represents a matched intent with confidence score
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentMatch {
    pub intent_name: String,
    pub provider_name: String,
    pub confidence: f64,
    pub trigger_pattern: String,
    pub original_input: String,
    pub entities: Vec<Entity>,
    pub source: String, // "rule_based" or "llm"
}

/// Represents an extracted entity from user input
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    pub entity_type: String, // 'path', 'file', 'process', 'number', etc.
    pub value: String,
    pub original: String,
    pub start: usize,
    pub end: usize,
}

/// Represents multiple possible matches requiring disambiguation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AmbiguousMatch {
    pub original_input: String,
    pub suggestions: Vec<IntentMatch>,
}

/// Represents a trigger pattern for intent matching
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trigger {
    pub pattern: String,
    pub intent_name: String,
    pub provider_name: String,
    pub weight: f64,
    pub aliases: Vec<String>,
}

/// Result type for parsing operations
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum ParseResult {
    #[serde(rename = "match")]
    Match(IntentMatch),
    #[serde(rename = "ambiguous")]
    Ambiguous(AmbiguousMatch),
    #[serde(rename = "none")]
    None,
}

impl IntentMatch {
    pub fn new(
        intent_name: String,
        provider_name: String,
        confidence: f64,
        trigger_pattern: String,
        original_input: String,
        source: String,
    ) -> Self {
        Self {
            intent_name,
            provider_name,
            confidence,
            trigger_pattern,
            original_input,
            entities: Vec::new(),
            source,
        }
    }
}

impl Entity {
    pub fn new(
        entity_type: String,
        value: String,
        original: String,
        start: usize,
        end: usize,
    ) -> Self {
        Self {
            entity_type,
            value,
            original,
            start,
            end,
        }
    }
}
