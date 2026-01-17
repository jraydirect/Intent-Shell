//! Fast string similarity calculation
//!
//! Optimized implementations of similarity algorithms for intent matching.

use ahash::AHashSet;

/// Calculate similarity score between input and pattern (0.0-1.0)
///
/// Uses a multi-stage approach:
/// 1. Exact substring match → 1.0
/// 2. Token-based overlap → 0.0-1.0
/// 3. Sequence similarity → 0.0-1.0
///
/// Optimized for <5ms performance.
pub fn calculate_similarity(input: &str, pattern: &str) -> f64 {
    // Fast path: exact substring match
    if pattern.is_empty() {
        return 0.0;
    }
    
    if input.contains(pattern) {
        return 1.0;
    }
    
    // Normalize strings (lowercase for matching)
    let input_lower = input.to_lowercase();
    let pattern_lower = pattern.to_lowercase();
    
    // Fast path: exact match after normalization
    if input_lower.contains(&pattern_lower) {
        return 0.95; // Slightly lower than exact case match
    }
    
    // Token-based matching (fast)
    let input_tokens: AHashSet<&str> = input_lower.split_whitespace().collect();
    let pattern_tokens: AHashSet<&str> = pattern_lower.split_whitespace().collect();
    
    if pattern_tokens.is_empty() {
        return 0.0;
    }
    
    let token_overlap = input_tokens
        .intersection(&pattern_tokens)
        .count() as f64
        / pattern_tokens.len() as f64;
    
    // Early exit if token overlap is too low
    if token_overlap < 0.3 {
        return token_overlap * 0.6;
    }
    
    // Sequence similarity (more expensive, but only if token overlap is promising)
    let sequence_similarity = sequence_ratio(&input_lower, &pattern_lower);
    
    // Weighted combination
    let score = (token_overlap * 0.6) + (sequence_similarity * 0.4);
    
    score
}

/// Calculate sequence similarity ratio (similar to difflib.SequenceMatcher.ratio)
///
/// Uses a simplified version of Ratcliff-Obershelp algorithm for speed.
fn sequence_ratio(s1: &str, s2: &str) -> f64 {
    if s1.is_empty() && s2.is_empty() {
        return 1.0;
    }
    if s1.is_empty() || s2.is_empty() {
        return 0.0;
    }
    
    // Use longest common subsequence for faster computation
    let lcs_len = longest_common_subsequence(s1, s2);
    let total_len = s1.chars().count() + s2.chars().count();
    
    if total_len == 0 {
        return 0.0;
    }
    
    (2.0 * lcs_len as f64) / total_len as f64
}

/// Calculate length of longest common subsequence (LCS)
///
/// This is faster than full Ratcliff-Obershelp for similarity scoring.
fn longest_common_subsequence(s1: &str, s2: &str) -> usize {
    let s1_chars: Vec<char> = s1.chars().collect();
    let s2_chars: Vec<char> = s2.chars().collect();
    
    let m = s1_chars.len();
    let n = s2_chars.len();
    
    // Use dynamic programming with space optimization
    let mut prev = vec![0; n + 1];
    let mut curr = vec![0; n + 1];
    
    for i in 1..=m {
        for j in 1..=n {
            if s1_chars[i - 1] == s2_chars[j - 1] {
                curr[j] = prev[j - 1] + 1;
            } else {
                curr[j] = prev[j].max(curr[j - 1]);
            }
        }
        std::mem::swap(&mut prev, &mut curr);
    }
    
    prev[n]
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_exact_match() {
        assert!((calculate_similarity("open desktop", "open desktop") - 1.0).abs() < 0.001);
    }
    
    #[test]
    fn test_substring_match() {
        assert!(calculate_similarity("open desktop folder", "open desktop") > 0.9);
    }
    
    #[test]
    fn test_token_overlap() {
        let score = calculate_similarity("open downloads folder", "open downloads");
        assert!(score > 0.7);
    }
    
    #[test]
    fn test_no_match() {
        let score = calculate_similarity("hello world", "open desktop");
        assert!(score < 0.3);
    }
}
