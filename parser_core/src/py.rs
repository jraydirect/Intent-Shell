//! Python bindings for parser core using PyO3

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use crate::types::{Trigger, ParseResult};
use crate::similarity::calculate_similarity;
use crate::matcher::match_intent;
use crate::entities::EntityExtractor;
use serde_json;

/// Calculate similarity between two strings (Python function)
#[pyfunction]
pub fn py_calculate_similarity(input: &str, pattern: &str) -> f64 {
    calculate_similarity(input, pattern)
}

/// Python wrapper for similarity calculator
#[pyclass]
pub struct PySimilarityCalculator;

#[pymethods]
impl PySimilarityCalculator {
    #[new]
    fn new() -> Self {
        Self
    }
    
    /// Calculate similarity score between input and pattern
    fn calculate(&self, input: &str, pattern: &str) -> f64 {
        calculate_similarity(input, pattern)
    }
}

/// Python wrapper for intent matcher
#[pyclass]
pub struct PyIntentMatcher {
    triggers: Vec<Trigger>,
}

#[pymethods]
impl PyIntentMatcher {
    #[new]
    fn new() -> Self {
        Self {
            triggers: Vec::new(),
        }
    }
    
    /// Add a trigger pattern
    fn add_trigger(
        &mut self,
        pattern: String,
        intent_name: String,
        provider_name: String,
        weight: f64,
        aliases: Vec<String>,
    ) {
        self.triggers.push(Trigger {
            pattern,
            intent_name,
            provider_name,
            weight,
            aliases,
        });
    }
    
    /// Add triggers from Python list of dicts (deprecated - use add_trigger instead)
    fn add_triggers_from_list(&mut self, _py: Python, triggers_list: Bound<'_, PyList>) -> PyResult<()> {
        for item in triggers_list.iter() {
            let trigger_dict = item.downcast::<PyDict>()?;
            
            let pattern: String = trigger_dict
                .get_item("pattern")?
                .and_then(|v| v.extract().ok())
                .unwrap_or_default();
            let intent_name: String = trigger_dict
                .get_item("intent_name")?
                .and_then(|v| v.extract().ok())
                .unwrap_or_default();
            let provider_name: String = trigger_dict
                .get_item("provider_name")?
                .and_then(|v| v.extract().ok())
                .unwrap_or_default();
            let weight: f64 = trigger_dict
                .get_item("weight")?
                .and_then(|v| v.extract().ok())
                .unwrap_or(1.0);
            let aliases: Vec<String> = trigger_dict
                .get_item("aliases")?
                .and_then(|v| v.extract().ok())
                .unwrap_or_default();
            
            self.add_trigger(pattern, intent_name, provider_name, weight, aliases);
        }
        
        Ok(())
    }
    
    /// Match user input against triggers
    fn match_intent<'py>(&self, input: &str, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let result = match_intent(input, &self.triggers);
        
        match result {
            ParseResult::Match(m) => {
                let dict = PyDict::new_bound(py);
                dict.set_item("type", "match")?;
                dict.set_item("intent_name", m.intent_name)?;
                dict.set_item("provider_name", m.provider_name)?;
                dict.set_item("confidence", m.confidence)?;
                dict.set_item("trigger_pattern", m.trigger_pattern)?;
                dict.set_item("original_input", m.original_input)?;
                dict.set_item("source", m.source)?;
                // Convert entities to Python list
                let entities_json = serde_json::to_string(&m.entities)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to serialize entities: {}", e)))?;
                dict.set_item("entities", entities_json)?;
                Ok(dict)
            }
            ParseResult::Ambiguous(a) => {
                let dict = PyDict::new_bound(py);
                dict.set_item("type", "ambiguous")?;
                dict.set_item("original_input", a.original_input)?;
                
                let suggestions: Vec<Bound<'_, PyDict>> = a.suggestions
                    .iter()
                    .map(|m| -> PyResult<Bound<'_, PyDict>> {
                        let m_dict = PyDict::new_bound(py);
                        m_dict.set_item("intent_name", &m.intent_name)?;
                        m_dict.set_item("provider_name", &m.provider_name)?;
                        m_dict.set_item("confidence", m.confidence)?;
                        m_dict.set_item("trigger_pattern", &m.trigger_pattern)?;
                        Ok(m_dict)
                    })
                    .collect::<PyResult<Vec<_>>>()?;
                
                dict.set_item("suggestions", suggestions)?;
                Ok(dict)
            }
            ParseResult::None => {
                let dict = PyDict::new_bound(py);
                dict.set_item("type", "none")?;
                Ok(dict)
            }
        }
    }
    
    /// Clear all triggers
    fn clear(&mut self) {
        self.triggers.clear();
    }
    
    /// Get number of triggers
    fn len(&self) -> usize {
        self.triggers.len()
    }
}

/// Python wrapper for entity extractor
#[pyclass]
pub struct PyEntityExtractor {
    extractor: EntityExtractor,
}

#[pymethods]
impl PyEntityExtractor {
    #[new]
    fn new() -> Self {
        Self {
            extractor: EntityExtractor::new(),
        }
    }
    
    /// Extract entities from text
    fn extract<'py>(&self, text: &str, py: Python<'py>) -> PyResult<Vec<Bound<'py, PyDict>>> {
        let entities = self.extractor.extract(text);
        
        entities
            .iter()
            .map(|e| -> PyResult<Bound<'py, PyDict>> {
                let dict = PyDict::new_bound(py);
                dict.set_item("type", &e.entity_type)?;
                dict.set_item("value", &e.value)?;
                dict.set_item("original", &e.original)?;
                dict.set_item("start", e.start)?;
                dict.set_item("end", e.end)?;
                Ok(dict)
            })
            .collect()
    }
}
