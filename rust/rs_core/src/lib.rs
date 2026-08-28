use pyo3::prelude::*;
use pyo3::exceptions::PyTypeError;
use pyo3::wrap_pyfunction;
use pyo3::types::PyType;
use pyo3::types::{PyDate, PyDateTime, PyAny, PyDict};
use rayon::prelude::*;
use chrono::{Datelike, Timelike, NaiveDate, NaiveTime, NaiveDateTime, DateTime};


#[pyfunction]
fn validate_datamodel(py: Python<'_>, dataclass_instance: Py<PyAny>) -> PyResult<Vec<(String, bool)>> {
    // Get the class of the instance
    let instance = dataclass_instance.bind(py);
    let dataclass = instance.get_type();

    // Get the __dataclass_fields__ attribute from the class
    let fields_attr = dataclass.getattr("__dataclass_fields__")?;
    let fields_dict = fields_attr.clone().cast_into::<PyDict>()?;

    // Validate each field in the main thread
    let results: Vec<(String, bool)> = fields_dict
        .items()
        .iter()
        .map(|item| {
            let (key, field): (String, Bound<'_, PyAny>) = item.extract().unwrap();

            // Extract information from the dataclass.Field object
            let field_type: Py<PyAny> = field.getattr("type").unwrap().unbind();
            let value: Py<PyAny> = dataclass_instance.getattr(py, key.as_str()).unwrap();

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

fn validate_field(py: Python<'_>, field_type: &Py<PyAny>, value: &Py<PyAny>) -> PyResult<bool> {
    // Check if it's a primitive type
    let field_type_bound = field_type.bind(py);
    if let Ok(type_) = field_type_bound.clone().cast_into::<PyType>() {
        let type_name = type_.name()?;
        match type_name.to_str()? {
            "str" => {
                return Ok(value.extract::<String>(py).is_ok());
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
                return Ok(value.bind(py).clone().cast_into::<PyDateTime>().is_ok());
            }
            "date" => {
                return Ok(value.bind(py).clone().cast_into::<PyDate>().is_ok());
            }
            _ => {
                let name_str = type_.name()?.to_str()?.to_string();
                return Err(PyTypeError::new_err(format!(
                    "Validation for type {} is not implemented yet.",
                    name_str
                )));
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
            FieldType::Str => true,
            FieldType::Int => true,
            FieldType::Float => true,
            FieldType::Bool => true,
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
}

// A Rust struct representing the minimal info we need from each dataclass Field
#[derive(Debug)]
struct RustFieldInfo {
    pub field_name: String,
    pub field_type: FieldType,
    #[allow(dead_code)]
    pub type_name: String,
    value: FieldValue,
}

/// Collect the minimal field data we need into native Rust structs
fn get_field_info(py: Python<'_>, dataclass_instance: &Py<PyAny>, fields_dict: &Bound<'_, PyDict>) -> PyResult<Vec<RustFieldInfo>> {
    let mut result = Vec::new();

    for (key, field_obj) in fields_dict.iter() {
        let field_name = key.extract::<String>()?;

        // Extract type name
        let type_obj = field_obj.getattr("type")?;
        let type_bound = type_obj.clone().cast_into::<PyType>()?;
        let type_name = type_bound.name()?.to_str()?.to_string();

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
fn parse_datamodel(py: Python<'_>, dataclass_instance: Py<PyAny>) -> PyResult<Vec<(String, bool)>> {
    // 1) Get dataclass instance's class
    let instance = dataclass_instance.bind(py);
    let dataclass_type = instance.get_type();

    // 2) Get __dataclass_fields__ from the class
    let fields_attr = dataclass_type.getattr("__dataclass_fields__")?;
    let fields_dict = fields_attr.clone().cast_into::<PyDict>()?;

    // 3) Convert Python fields into a native Rust Vec<RustFieldInfo>
    let field_infos = get_field_info(py, &dataclass_instance, &fields_dict)?;

    // 4) Perform parallel iteration over `field_infos`
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
}


/// Python module declaration
#[pymodule]
fn rs_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate_datamodel, m)?)?;
    m.add_function(wrap_pyfunction!(parse_datamodel, m)?)?;
    Ok(())
}
