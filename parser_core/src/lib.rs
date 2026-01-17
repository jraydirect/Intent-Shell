//! Parser core - High-performance Rust implementation of semantic matching
//! 
//! This module provides fast intent matching, entity extraction, and similarity
//! calculation for IntelliShell's semantic parser.

pub mod types;
pub mod similarity;
pub mod matcher;
pub mod entities;

pub use types::*;
pub use similarity::*;
pub use matcher::*;
pub use entities::*;

// Python bindings
#[cfg(feature = "extension-module")]
pub mod py;

#[cfg(feature = "extension-module")]
use pyo3::prelude::*;

#[cfg(feature = "extension-module")]
#[pymodule]
fn parser_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    use py::*;
    m.add_class::<PySimilarityCalculator>()?;
    m.add_class::<PyIntentMatcher>()?;
    m.add_class::<PyEntityExtractor>()?;
    m.add_function(wrap_pyfunction!(py_calculate_similarity, m)?)?;
    Ok(())
}
