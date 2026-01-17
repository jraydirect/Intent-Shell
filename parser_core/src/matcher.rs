//! Intent matcher - Fast matching of user input against trigger patterns

use crate::types::{IntentMatch, Trigger, ParseResult, AmbiguousMatch};
use crate::similarity::calculate_similarity;

/// Confidence thresholds for matching
pub const CONFIDENCE_THRESHOLD: f64 = 0.90; // Very high confidence: execute directly
pub const MIN_CONFIDENCE: f64 = 0.50; // Minimum for rule-based
pub const AMBIGUITY_ZONE_START: f64 = 0.60;
pub const AMBIGUITY_ZONE_END: f64 = 0.90;

/// Match user input against a list of triggers
///
/// Returns the best match, ambiguous matches, or none if no good match found.
pub fn match_intent(input: &str, triggers: &[Trigger]) -> ParseResult {
    if triggers.is_empty() {
        return ParseResult::None;
    }
    
    // Normalize input
    let input_normalized = input.to_lowercase().trim().to_string();
    let input_normalized_str = input_normalized.as_str();
    
    // Score all triggers
    let mut scored_matches: Vec<(IntentMatch, f64)> = Vec::with_capacity(triggers.len());
    
    for trigger in triggers {
        // Check exact pattern
        let pattern_score = calculate_similarity(input_normalized_str, &trigger.pattern);
        
        // Check aliases
        let mut best_score = pattern_score;
        for alias in &trigger.aliases {
            let alias_score = calculate_similarity(input_normalized_str, alias);
            if alias_score > best_score {
                best_score = alias_score;
            }
        }
        
        // Apply weight
        let final_score = best_score * trigger.weight;
        
        if final_score >= MIN_CONFIDENCE {
            let intent_match = IntentMatch::new(
                trigger.intent_name.clone(),
                trigger.provider_name.clone(),
                final_score,
                trigger.pattern.clone(),
                input.to_string(),
                "rule_based".to_string(),
            );
            
            scored_matches.push((intent_match, final_score));
        }
    }
    
    if scored_matches.is_empty() {
        return ParseResult::None;
    }
    
    // Sort by score (descending)
    scored_matches.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    
    let best_match = &scored_matches[0];
    let best_score = best_match.1;
    
    // Very high confidence - return directly
    if best_score >= CONFIDENCE_THRESHOLD {
        return ParseResult::Match(best_match.0.clone());
    }
    
    // Check for ambiguity (multiple close matches)
    if best_score >= AMBIGUITY_ZONE_START && best_score < AMBIGUITY_ZONE_END {
        // Find all matches within 0.1 of best score
        let ambiguity_threshold = best_score - 0.1;
        let ambiguous: Vec<IntentMatch> = scored_matches
            .iter()
            .take(5) // Limit to top 5
            .filter(|(_, score)| *score >= ambiguity_threshold)
            .map(|(match_, _)| match_.clone())
            .collect();
        
        if ambiguous.len() > 1 {
            return ParseResult::Ambiguous(AmbiguousMatch {
                original_input: input.to_string(),
                suggestions: ambiguous,
            });
        }
    }
    
    // Single match but below threshold (return anyway)
    if best_score >= MIN_CONFIDENCE {
        return ParseResult::Match(best_match.0.clone());
    }
    
    ParseResult::None
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_exact_match() {
        let triggers = vec![
            Trigger {
                pattern: "open desktop".to_string(),
                intent_name: "open_desktop".to_string(),
                provider_name: "filesystem".to_string(),
                weight: 1.0,
                aliases: Vec::new(),
            },
        ];
        
        match match_intent("open desktop", &triggers) {
            ParseResult::Match(m) => {
                assert_eq!(m.intent_name, "open_desktop");
                assert!(m.confidence >= 0.9);
            }
            _ => panic!("Expected match"),
        }
    }
    
    #[test]
    fn test_no_match() {
        let triggers = vec![
            Trigger {
                pattern: "open desktop".to_string(),
                intent_name: "open_desktop".to_string(),
                provider_name: "filesystem".to_string(),
                weight: 1.0,
                aliases: Vec::new(),
            },
        ];
        
        match match_intent("completely unrelated query", &triggers) {
            ParseResult::None => {}
            _ => panic!("Expected no match"),
        }
    }
}
