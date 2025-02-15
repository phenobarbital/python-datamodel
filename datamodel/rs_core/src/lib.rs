use pyo3::prelude::*;
// use pyo3::exceptions::PyValueError;
use pyo3::exceptions::PyTypeError;
use pyo3::wrap_pyfunction;
use pyo3::types::PyType;
use pyo3::types::{PyDate, PyDateTime, PyAny, PyDict};
// use pyo3::PyTypeInfo;
// use chrono::{Datelike, Timelike, NaiveDate, NaiveTime, NaiveDateTime, DateTime, Utc};
use rayon::prelude::*;
// use std::collections::HashMap;


#[pyfunction]
fn validate_datamodel(py: Python<'_>, dataclass_instance: PyObject) -> PyResult<Vec<(String, bool)>> {
    // Get the class of the instance
    let dataclass: &PyType = dataclass_instance.as_ref(py).get_type();

    // Get the __dataclass_fields__ attribute from the class
    let fields_dict: &PyDict = dataclass.getattr("__dataclass_fields__")?.downcast::<PyDict>()?;

    // Validate each field in the main thread
    let results: Vec<(String, bool)> = fields_dict
        .items()
        .iter()
        .map(|item| {
            let (key, field) = item.extract::<(String, &PyAny)>().unwrap();

            // Extract information from the dataclass.Field object
            let field_type = field.getattr("type").unwrap().to_object(py);
            let value = dataclass_instance.getattr(py, key.as_str()).unwrap();

            let is_valid = match validate_field(py, &field_type, &value) {
                Ok(result) => result,
                Err(e) => {
                    eprintln!("Validation error for field {}: {}", key, e);
                    false
                }
            };
            (key.to_string(), is_valid)
        })
        .collect();

    Ok(results)
}

fn validate_field(py: Python<'_>, field_type: &PyObject, value: &PyObject) -> PyResult<bool> {
    // Check if it's a primitive type
    if let Ok(type_) = field_type.extract::<&PyType>(py) {
        let type_name = type_.name()?;
        match type_name {
            "str" => {
                return Ok(value.extract::<&str>(py).is_ok());
            }
            "int" => {
                return Ok(value.extract::<i64>(py).is_ok());
            }
            "float" => {
                return Ok(value.extract::<f64>(py).is_ok());
            }
            "bool" => {
                return Ok(value.extract::<bool>(py).is_ok());
            }
            "datetime" => {
                return Ok(value.extract::<&PyDateTime>(py).is_ok());
            }
            "date" => {
                return Ok(value.extract::<&PyDate>(py).is_ok());
            }
            _ => {
                // Not a primitive type, you can either skip validation or return an error
                // eprintln!("Skipping validation for non-primitive type: {}", type_name);
                // Ok(true) // Option 1: Skip validation
                return Err(PyTypeError::new_err(format!(
                    "Validation for type {} is not implemented yet.",
                    type_name
                ))); // Option 2: Return an error
            }
        }
    } else {
        // Handle the case where field_type is not a PyType (e.g., it's a generic type)
        eprintln!("Field type is not a PyType: {:?}", field_type);
        return Err(PyTypeError::new_err(
            "Field type is not a PyType, cannot validate.",
        ));
    }
}

#[derive(Debug)]
enum FieldType {
    Str,
    Int,
    Float,
    Bool,
    DateTime,
    Date,
    Time,
    // Extend with more types as needed
}

impl FieldType {
    /// Convert type name string to FieldType enum
    fn from_str(type_name: &str) -> Option<Self> {
        match type_name {
            "str" => Some(FieldType::Str),
            "int" => Some(FieldType::Int),
            "float" => Some(FieldType::Float),
            "bool" => Some(FieldType::Bool),
            "datetime.datetime" => Some(FieldType::DateTime),
            "datetime.date" => Some(FieldType::Date),
            "datetime.time" => Some(FieldType::Time),
            _ => None,
        }
    }

    /// Parse the string representation into Rust-native types if necessary
    fn parse(&self, value: &FieldValue) -> bool {
        match self {
            FieldType::Str => true, // Already a string
            FieldType::Int => true, // Already an integer
            FieldType::Float => true, // Already a float
            FieldType::Bool => true, // Already a bool
            FieldType::DateTime => {
                if let FieldValue::Str(s) = value {
                    DateTime::parse_from_rfc3339(s).is_ok()
                } else {
                    false
                }
            },
            FieldType::Date => {
                if let FieldValue::Str(s) = value {
                    NaiveDate::parse_from_str(s, "%Y-%m-%d").is_ok()
                } else {
                    false
                }
            },
            FieldType::Time => {
                if let FieldValue::Str(s) = value {
                    NaiveTime::parse_from_str(s, "%H:%M:%S").is_ok()
                } else {
                    false
                }
            },
            // Implement other parsing as needed
        }
    }

    /// Validate the PyObject against the FieldType
    fn validate(&self, value: &FieldValue) -> bool {
        match self {
            FieldType::Str => matches!(value, FieldValue::Str(_)),
            FieldType::Int => matches!(value, FieldValue::Int(_)),
            FieldType::Float => matches!(value, FieldValue::Float(_)),
            FieldType::Bool => matches!(value, FieldValue::Bool(_)),
            FieldType::DateTime => matches!(value, FieldValue::DateTime(_)),
            FieldType::Date => matches!(value, FieldValue::Date(_)),
            FieldType::Time => matches!(value, FieldValue::Time(_)),
            // Add more validations as needed
        }
    }
}

/// Enum representing the Rust-native value of a field
#[derive(Debug)]
enum FieldValue {
    Str(String),
    Int(i64),
    Float(f64),
    Bool(bool),
    DateTime(String), // Store as String; parse validation done separately
    Date(String),
    Time(String),
    // Extend with more types as needed
}

// A Rust struct representing the minimal info we need from each dataclass Field
#[derive(Debug)]
struct RustFieldInfo {
    pub field_name: String,
    pub field_type: FieldType,
    pub type_name: String, // Assuming type is always present for simplicity
    value: FieldValue,
}

/// Collect the minimal field data we need into native Rust structs
fn get_field_info(py: Python<'_>, dataclass_instance: &PyObject, fields_dict: &PyDict) -> PyResult<Vec<RustFieldInfo>> {
    let mut result = Vec::new();

    for (key, field_obj) in fields_dict.iter() {
        let field_name = key.extract::<String>()?;

        // Extract type name
        let type_obj = field_obj.getattr("type")?;
        let type_name = type_obj.extract::<&PyType>()?.name()?.to_string();

        // Convert type name to FieldType enum
        let field_type = match FieldType::from_str(&type_name) {
            Some(ft) => ft,
            None => continue, // Skip unsupported types or handle as needed
        };

        // Extract value
        let py_value = dataclass_instance.getattr(py, &field_name[..])?;

        // Convert PyObject to Rust-native FieldValue
        let value = match field_type {
            FieldType::Str => {
                FieldValue::Str(py_value.extract::<String>(py)?)
            },
            FieldType::Int => {
                FieldValue::Int(py_value.extract::<i64>(py)?)
            },
            FieldType::Float => {
                FieldValue::Float(py_value.extract::<f64>(py)?)
            },
            FieldType::Bool => {
                FieldValue::Bool(py_value.extract::<bool>(py)?)
            },
            FieldType::DateTime => {
                let s: String = py_value.extract::<String>(py)?;
                FieldValue::DateTime(s)
            },
            FieldType::Date => {
                let s: String = py_value.extract::<String>(py)?;
                FieldValue::Date(s)
            },
            FieldType::Time => {
                let s: String = py_value.extract::<String>(py)?;
                FieldValue::Time(s)
            },
            // Handle other types as needed
        };

        result.push(RustFieldInfo {
            field_name,
            field_type,
            type_name,
            value,
        });
    }

    Ok(result)
}

/// A mock-up function that showcases a single iteration over fields
/// performing these steps:
/// 1) Handle `default` or `default_factory` if the field is missing
/// 2) Parse the field's value (e.g. str -> UUID, str -> date, etc.)
/// 3) Validate the resulting value against the annotated type
#[pyfunction]
fn parse_datamodel(py: Python<'_>, dataclass_instance: PyObject) -> PyResult<Vec<(String, bool)>> {
    // Acquire the GIL using `Python::with_gil`
    Python::with_gil(|py| {
        // 1) Get dataclass instance's class
        let dataclass_type: &PyType = dataclass_instance.as_ref(py).get_type();

        // 2) Get __dataclass_fields__ from the class
        let fields_dict: &PyDict = dataclass_type
            .getattr("__dataclass_fields__")?
            .downcast::<PyDict>()?;

        // 3) Convert Python fields into a native Rust Vec<RustFieldInfo>
        let field_infos = get_field_info(py, &dataclass_instance, fields_dict)?;

        // 4) Drop the GIL before parallel processing
        // Note: `Python::with_gil` automatically drops the GIL when the closure ends
        // Hence, no need to explicitly drop `py` here

        // 5) Perform parallel iteration over `field_infos`
        let results: Vec<(String, bool)> = field_infos
            .into_par_iter()
            .map(|field_info| {
                // Perform parsing and validation purely in Rust
                let is_parsed = field_info.field_type.parse(&field_info.value);
                if !is_parsed {
                    return (field_info.field_name, false);
                }

                let is_valid = field_info.field_type.validate(&field_info.value);
                (field_info.field_name, is_valid)
            })
            .collect();

        Ok(results)
    })
}


/// Python module declaration
#[pymodule]
fn rs_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate_datamodel, m)?)?;
    m.add_function(wrap_pyfunction!(parse_datamodel, m)?)?;
    Ok(())
}
