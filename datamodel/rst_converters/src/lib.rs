use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use pyo3::exceptions::PyTypeError;
use pyo3::wrap_pyfunction;
use pyo3::types::PyType;
use pyo3::types::{PyDate, PyDateTime, PyAny, PyDict, PyTime};
// use pyo3::PyTypeInfo;
use chrono::{Datelike, Timelike, NaiveDate, NaiveTime, NaiveDateTime, DateTime, Utc};
use speedate::Date as SpeeDate;
use speedate::DateTime as SpeeDateTime;
// use speedate::{Date, DateTime, ParseError};
use rayon::prelude::*;
// use std::collections::HashMap;


/// Converts a string representation of truth to a boolean.
///
/// # Arguments
/// * `val` - The string value to convert.
///
/// # Returns
/// * `Ok(bool)` - True or False if conversion is successful.
/// * `Err(PyValueError)` - Raised if the input string cannot be interpreted as boolean.
#[pyfunction]
fn strtobool(val: &str) -> PyResult<bool> {
    let lower_val = &val.trim().to_lowercase();
    //let mut input: &mut str = val; //you could also add the mut above
    //input.make_ascii_lowercase();
    // let lower_val: &str = input.trim();

    match lower_val.as_str() {
        "y" | "yes" | "t" | "true" | "on" | "1" => Ok(true),
        "n" | "no" | "f" | "false" | "off" | "0" => Ok(false),
        _ => Err(PyValueError::new_err(format!(
            "Invalid truth value for '{}'",
            val
        ))),
    }
}

/// Converts any object value to a boolean representation.
///
/// # Arguments
/// * `obj` - A PyObject to convert.
///
/// # Returns
/// * Boolean or None if the object is None.
#[pyfunction]
fn to_boolean(_py: Python, obj: Option<&PyAny>) -> PyResult<Option<bool>> {
    match obj {
        Some(val) => {
            if val.is_none() {
                Ok(None)
            } else if let Ok(b) = val.extract::<bool>() {
                Ok(Some(b))
            } else if let Ok(s) = val.extract::<String>() {
                Ok(Some(strtobool(&s)?))
            } else if val.is_callable() {
                match val.call0() {
                    Ok(res) => Ok(Some(res.extract::<bool>()?)),
                    Err(_) => Ok(None),
                }
            } else {
                Ok(Some(val.is_true()?))
            }
        }
        None => Ok(None),
    }
}

#[pyfunction]
fn to_timestamp(py: Python, timestamp: f64) -> PyResult<PyObject> {
    let seconds = timestamp.floor() as i64;
    let microseconds = (timestamp.fract() * 1_000_000.0).round() as u32;
    // let naive_dt = NaiveDateTime::from_timestamp_opt(seconds, microseconds);
    let datetime = DateTime::<Utc>::from_timestamp(seconds, microseconds);
    if let Some(dt) = datetime {
        let naive_dt: NaiveDateTime = dt.naive_utc();
        Ok(PyDateTime::new(
            py,
            naive_dt.date().year(),
            naive_dt.date().month() as u8,
            naive_dt.date().day() as u8,
            naive_dt.time().hour() as u8,
            naive_dt.time().minute() as u8,
            naive_dt.time().second() as u8,
            naive_dt.and_utc().timestamp_subsec_micros() as u32,
            None,
        )?
        .into_py(py))
    } else {
        return Err(PyValueError::new_err("Invalid timestamp"));
    }
}

/// Parses a string into a `NaiveDate` using multiple formats.
///
/// # Arguments
/// * `input` - The string to parse.
///
/// # Returns
/// * `Ok(NaiveDate)` if parsing succeeds.
/// * `Err(PyValueError)` if no format matches.
#[pyfunction]
fn to_date(py: Python, input: &str, custom_format: Option<&str>) -> PyResult<Py<PyDate>> {
    if input.trim().is_empty() {
        return Err(PyValueError::new_err("Input string is empty"));
    }

    // Use speedate for ISO 8601 parsing
    if let Ok(parsed_date) = SpeeDate::parse_str(input) {
        return Ok(PyDate::new(
            py,
            parsed_date.year as i32,
            parsed_date.month,
            parsed_date.day,
        )?
        .into_py(py));
    }

    // Define custom formats to try, including the optional format.
    let formats = vec![
        "%Y-%m-%d",             // ISO 8601 date
        "%m/%d/%Y",             // Month/day/year
        "%m-%d-%Y",             // Month-day-year
        "%d-%m-%Y",             // Custom format
        "%Y/%m/%d",             // Slash-separated date
        "%Y-%m-%dT%H:%M:%S%.f", // ISO 8601 datetime
        "%Y-%m-%d %H:%M:%S",    // ISO 8601 with time
        "%d/%m/%Y",             // Day/month/year
        "%d.%m.%Y",             // Day.month.year
        custom_format.unwrap_or_default(),
    ];

    for &fmt in &formats {
        if let Ok(date) = NaiveDate::parse_from_str(input, fmt) {
            return Ok(PyDate::new(py, date.year(), date.month() as u8, date.day() as u8)?.into_py(py));
        }
    }

    Err(PyValueError::new_err(format!(
        "Unable to parse input '{}' into a date. Accepted types are strings (ISO 8601 or custom formats)",
        input
    )))
}

#[pyfunction]
fn to_datetime(py: Python, input: &str, custom_format: Option<&str>) -> PyResult<Py<PyDateTime>> {

    if input.trim().is_empty() {
        return Err(PyValueError::new_err("Input string is empty"));
    }

    // Attempt parsing using Speedate
    if let Ok(parsed_datetime) = SpeeDateTime::parse_str(input) {
        return Ok(PyDateTime::new(
            py,
            parsed_datetime.date.year as i32,
            parsed_datetime.date.month,
            parsed_datetime.date.day,
            parsed_datetime.time.hour,
            parsed_datetime.time.minute,
            parsed_datetime.time.second,
            parsed_datetime.time.microsecond,
            None,
        )?
        .into_py(py));
    }

    // Try parsing as ISO 8601 datetime with timezone.
    if let Ok(datetime) = DateTime::parse_from_rfc3339(input) {
        let datetime_utc = datetime.with_timezone(&Utc);
        return Ok(PyDateTime::from_timestamp(py, datetime_utc.timestamp() as f64, None)?.into_py(py));
    }

    // Try parsing as ISO 8601 datetime without fractional seconds.
    if let Ok(datetime) = NaiveDateTime::parse_from_str(input, "%Y-%m-%dT%H:%M:%S") {
        return Ok(PyDateTime::new(py, datetime.date().year(), datetime.date().month() as u8, datetime.date().day() as u8,
            datetime.time().hour() as u8, datetime.time().minute() as u8, datetime.time().second() as u8, 0, None)?.into_py(py));
    }

    // Try parsing as ISO 8601 datetime with fractional seconds.
    if let Ok(datetime) = NaiveDateTime::parse_from_str(input, "%Y-%m-%dT%H:%M:%S%.f") {
        let microseconds = datetime.and_utc().timestamp_micros() as u32 % 1_000_000;
        return Ok(PyDateTime::new(py, datetime.date().year(), datetime.date().month() as u8, datetime.date().day() as u8,
            datetime.time().hour() as u8, datetime.time().minute() as u8, datetime.time().second() as u8, microseconds, None)?.into_py(py));
    }

    // Define custom formats to try, including the optional format.
    let formats = vec![
        "%Y-%m-%d",             // ISO 8601 date
        "%m/%d/%Y",             // Month/day/year
        "%m-%d-%Y",             // Month-day-year
        "%d-%m-%Y",             // Custom format
        "%Y/%m/%d",             // Slash-separated date
        "%Y-%m-%dT%H:%M:%S%.f", // ISO 8601 datetime
        "%Y-%m-%d %H:%M:%S",    // ISO 8601 with time
        "%d/%m/%Y",             // Day/month/year
        "%d.%m.%Y",             // Day.month.year
        custom_format.unwrap_or_default(),
    ];

    // Attempt parsing with each format.
    for &fmt in &formats {
        if let Ok(datetime) = NaiveDateTime::parse_from_str(input, fmt) {
            let microseconds = datetime.and_utc().timestamp_micros() as u32 % 1_000_000;
            return Ok(PyDateTime::new(py, datetime.date().year(), datetime.date().month() as u8, datetime.date().day() as u8,
                datetime.time().hour() as u8, datetime.time().minute() as u8, datetime.time().second() as u8, microseconds, None)?.into_py(py));
        }
    }

    // If all attempts fail, raise a ValueError.
    Err(PyValueError::new_err(format!(
        "Unable to parse datetime from '{}'. Tried formats: {:?}",
        input, formats
    )))
}

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


// /// Handle defaults and default_factories for a field
// fn handle_defaults(
//     py: Python<'_>,
//     dataclass_instance: &PyObject,
//     field_info: &RustFieldInfo,
// ) -> PyResult<()> {
//     let has_attr = dataclass_instance.as_ref(py).hasattr(field_info.field_name.as_str())?;
//     if !has_attr {
//         // If the dataclass instance doesn't have this attr, attempt to set
//         if field_info.has_default {
//             // Retrieve the default value
//             let dataclass_type: &PyType = dataclass_instance.as_ref(py).get_type();
//             let fields_dict: &PyDict = dataclass_type.getattr("__dataclass_fields__")?.downcast::<PyDict>()?;
//             if let Some(field_obj) = fields_dict.get_item(&field_info.field_name) {
//                 let default_value = field_obj.getattr("default")?;
//                 // Only set if default is not MISSING
//                 if !default_value.is_none() {
//                     dataclass_instance.setattr(py, field_info.field_name.as_str(), default_value)?;
//                 }
//             }
//         } else if field_info.has_default_factory {
//             // Retrieve and call the default_factory
//             let dataclass_type: &PyType = dataclass_instance.as_ref(py).get_type();
//             let fields_dict: &PyDict = dataclass_type.getattr("__dataclass_fields__")?.downcast::<PyDict>()?;
//             if let Some(field_obj) = fields_dict.get_item(&field_info.field_name) {
//                 let default_factory = field_obj.getattr("default_factory")?;
//                 if default_factory.is_callable() {
//                     let factory_value = default_factory.call0()?;
//                     dataclass_instance.setattr(py, field_info.field_name.as_str(), factory_value)?;
//                 }
//             }
//         }
//     }
//     Ok(())
// }

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
fn rst_converters(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(strtobool, m)?)?;
    m.add_function(wrap_pyfunction!(to_boolean, m)?)?;
    m.add_function(wrap_pyfunction!(to_date, m)?)?;
    m.add_function(wrap_pyfunction!(to_datetime, m)?)?;
    m.add_function(wrap_pyfunction!(to_timestamp, m)?)?;
    m.add_function(wrap_pyfunction!(validate_datamodel, m)?)?;
    m.add_function(wrap_pyfunction!(parse_datamodel, m)?)?;
    Ok(())
}
