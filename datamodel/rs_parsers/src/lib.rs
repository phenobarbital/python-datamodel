use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use pyo3::PyTypeInfo;
use pyo3::wrap_pyfunction;
use pyo3::types::{PyDate, PyDateTime, PyAny, PyString, PyBool, PyBytes, PyInt, PyFloat, PyList};
use chrono::{Datelike, Timelike, NaiveDate, NaiveDateTime, DateTime, Utc};
use speedate::Date as SpeeDate;
use std::sync::Mutex;
use speedate::DateTime as SpeeDateTime;
use uuid::Uuid;
use rust_decimal::Decimal; // Rust Decimal crate
use rust_decimal::prelude::FromStr;
use rayon::prelude::*;
// use speedate::{Date, DateTime, ParseError};
// use std::collections::HashMap;
// NaiveTime


#[pyfunction]
#[pyo3(signature = (obj=None))]
fn to_string(py: Python, obj: Option<Py<PyAny>>) -> PyResult<Option<String>> {
    // If the object is None, return None
    match obj {
        None => Ok(None),
        Some(py_obj) => {
            let val = py_obj.bind(py);
            if val.is_none() {
                Ok(None)
            } else if val.is_instance(&PyString::type_object(py))? {
                // If the object is already a string, return it
                Ok(Some(val.extract::<String>()?))
            } else if val.is_instance(&PyBytes::type_object(py))? {
                // If the object is bytes, decode it to a string
                let bytes = val.downcast::<PyBytes>()?;
                Ok(Some(String::from_utf8(bytes.as_bytes().to_vec())?))
            } else if val.is_callable() {
                // If the object is callable, call it and convert the result to a string
                match val.call0()?.extract::<String>() {
                    Ok(result) => Ok(Some(result)),
                    Err(_) => Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                        "Callable did not return a string",
                    )),
                }
            } else {
                // Try converting the object to a string
                match val.str()?.to_str() {
                    Ok(string_rep) => Ok(Some(string_rep.to_string())),
                    Err(_) => Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                        "Object could not be converted to a string",
                    )),
                }
            }
        }
    }
}

#[pyfunction]
#[pyo3(signature = (py_type, input_list))]
fn to_list(py: Python, py_type: Py<PyAny>, input_list: Py<PyList>) -> PyResult<PyObject> {
    let input_list = input_list.bind(py);

    // Ensure py_type is callable
    let py_type = py_type.bind(py);
    if !py_type.is_callable() {
        return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>("Provided type is not callable"));
    }

    let mut result_list: Vec<PyObject> = Vec::new();

    for item in input_list.iter() {
        let converted_item = Python::with_gil(|py| {
            let py_type = py_type.clone();
            let item_obj: PyObject = item.into();
            py_type.call1((item_obj,)).map(|obj| obj.into())
        });
        result_list.push(converted_item?);
    }

    Python::with_gil(|py| {
        let py_list = PyList::new(py, &result_list)?;
        Ok(py_list.into())
    })
}

#[pyfunction]
#[pyo3(signature = (obj))]
fn slugify_camelcase(obj: String) -> String {
    // Return the original string if it's empty
    if obj.is_empty() {
        return obj;
    }

    // Initialize the resulting string with the first character
    let mut slugified = String::with_capacity(obj.len());
    let mut chars = obj.chars();
    if let Some(first_char) = chars.next() {
        slugified.push(first_char);
    }

    // Process the rest of the string
    for c in chars {
        // Check if the current character is uppercase and the previous character isn't a space
        if c.is_uppercase() && !slugified.ends_with(' ') {
            slugified.push(' '); // Insert a space before the uppercase character
        }
        slugified.push(c);
    }

    slugified
}

/// Converts a string representation of truth to a boolean.
///
/// # Arguments
/// * `val` - The string value to convert.
///
/// # Returns
/// * `Ok(bool)` - True or False if conversion is successful.
/// * `Err(PyValueError)` - Raised if the input string cannot be interpreted as boolean.
#[pyfunction]
#[pyo3(signature = (val))]
fn strtobool(val: &str) -> PyResult<bool> {
    match val.trim().to_lowercase().as_str() {
        "y" | "yes" | "t" | "true" | "on" | "1" => Ok(true),
        "n" | "no" | "f" | "false" | "off" | "0" | "none" | "null" => Ok(false),
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Invalid boolean string: '{}'",
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
#[pyo3(signature = (obj=None))]
fn to_boolean(py: Python, obj: Option<Py<PyAny>>) -> PyResult<Option<bool>> {
    match obj {
        Some(val) => {
            let val_ref = val.bind(py);
            if val_ref.is_none() {
                Ok(None)
            } else if val_ref.is_instance(&PyBool::type_object(py))? {
                Ok(Some(val.extract::<bool>(py)?))
            } else if val_ref.is_instance(&PyString::type_object(py))? {
                let py_str = val_ref.downcast::<PyString>()?;
                Ok(Some(strtobool(py_str.to_str()?)?))
            } else if let Ok(b) = val_ref.call_method0("__bool__")?.extract::<bool>() {
                Ok(Some(b))
            } else {
                Ok(Some(false))
            }
        }
        None => Ok(None),
    }
}


// Return the timestamp (int, float) as a Python datetime object.
#[pyfunction]
#[pyo3(signature = (timestamp))]
fn to_timestamp(py: Python, timestamp: f64) -> PyResult<Py<PyDateTime>> {
    // Split the timestamp into seconds and microseconds
    let seconds = timestamp.floor() as i64;
    let microseconds = ((timestamp - seconds as f64) * 1_000_000.0).round() as u32;

    // Validate the timestamp range to prevent panic
    if seconds < NaiveDateTime::MIN.and_utc().timestamp() || seconds > NaiveDateTime::MAX.and_utc().timestamp() {
        return Err(PyValueError::new_err("Invalid timestamp"));
    }

    // Create a NaiveDateTime from the split values
    if let Some(datetime) = DateTime::from_timestamp(seconds, microseconds) {
        // Construct a PyDateTime object
        let py_date = PyDateTime::new(
            py,
            datetime.date_naive().year(),
            datetime.date_naive().month() as u8,
            datetime.date_naive().day() as u8,
            datetime.time().hour() as u8,
            datetime.time().minute() as u8,
            datetime.time().second() as u8,
            datetime.time().nanosecond() / 1_000, // Convert nanoseconds to microseconds
            None,
        )?;
        Ok(py_date.into())
    } else {
        // Handle invalid timestamps
        Err(PyValueError::new_err("Invalid timestamp"))
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
#[pyo3(signature = (input, custom_format=None))]
fn to_date(py: Python, input: &str, custom_format: Option<&str>) -> PyResult<Py<PyDate>> {
    // Raise an error if the input is empty
    if input.trim().is_empty() {
        return Err(PyValueError::new_err("Input string is empty"));
    }

    // Attempt parsing using Speedate
    if let Ok(parsed_date) = SpeeDate::parse_str(input) {
        return Ok(PyDate::new(
            py,
            parsed_date.year as i32,
            parsed_date.month as u8,
            parsed_date.day as u8,
        )?.into());
    }

    // Define custom formats to try, including the optional format.
    let mut formats = vec![
        "%Y-%m-%d",             // ISO 8601 date
        "%m/%d/%Y",             // Month/day/year
        "%m-%d-%Y",             // Month-day-year
        "%d-%m-%Y",             // Custom format
        "%Y/%m/%d",             // Slash-separated date
        "%Y-%m-%dT%H:%M:%S%.f", // ISO 8601 datetime
        "%Y-%m-%d %H:%M:%S",    // ISO 8601 with time
        "%d/%m/%Y",             // Day/month/year
        "%d.%m.%Y",             // Day.month.year
    ];

    if let Some(fmt) = custom_format {
        formats.push(fmt);
    }

    // Attempt parsing with each format
    for &fmt in &formats {
        if let Ok(date) = NaiveDate::parse_from_str(input, fmt) {
            return Ok(PyDate::new(
                py,
                date.year(),
                date.month() as u8,
                date.day() as u8,
            )?.into());
        }
    }

    // Raise an error if no format matched
    Err(PyValueError::new_err(format!(
        "Unable to parse input '{}' into a date. Accepted formats: {:?}",
        input, formats
    )))
}


// Convert a string representation to a datetime object.
#[pyfunction]
#[pyo3(signature = (input, custom_format=None))]
fn to_datetime(py: Python, input: &str, custom_format: Option<&str>) -> PyResult<Py<PyDateTime>> {

    if input.trim().is_empty() {
        return Err(PyValueError::new_err("Input string is empty"));
    }

    // Attempt parsing using Speedate
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
        )?.into());
    }

    // Try parsing as ISO 8601 datetime with timezone.
    if let Ok(datetime) = DateTime::parse_from_rfc3339(input) {
        let datetime_utc = datetime.with_timezone(&Utc);
        return Ok(
            PyDateTime::from_timestamp(py, datetime_utc.timestamp() as f64, None,)?.into()
        );
    }

    // Define custom formats to try, including the optional format.
    let mut formats = vec![
        "%Y-%m-%d",             // ISO 8601 date
        "%m/%d/%Y",             // Month/day/year
        "%m-%d-%Y",             // Month-day-year
        "%d-%m-%Y",             // Custom format
        "%Y/%m/%d",             // Slash-separated date
        "%Y-%m-%dT%H:%M:%S%.f", // ISO 8601 datetime
        "%Y-%m-%d %H:%M:%S",    // ISO 8601 with time
        "%d/%m/%Y",             // Day/month/year
        "%d.%m.%Y",             // Day.month.year
    ];

    if let Some(fmt) = custom_format {
        formats.push(fmt);
    }

    // Attempt parsing with each format.
    for &fmt in &formats {
        if let Ok(datetime) = NaiveDateTime::parse_from_str(input, fmt) {
            let microseconds = datetime.and_utc().timestamp_micros() as u32 % 1_000_000;
            let py_date: Py<PyDateTime> = PyDateTime::new(
                py,
                datetime.date().year(),
                datetime.date().month() as u8,
                datetime.date().day() as u8,
                datetime.time().hour() as u8,
                datetime.time().minute() as u8,
                datetime.time().second() as u8,
                microseconds,
                None,
            )?.into();
            return Ok(py_date);
        }
    }

    // If all attempts fail, raise a ValueError.
    Err(PyValueError::new_err(format!(
        "Unable to parse datetime from '{}'. Tried formats: {:?}",
        input, formats
    )))
}

#[pyfunction]
#[pyo3(signature = (obj=None))]
fn to_uuid_obj(py: Python, obj: Option<Py<PyAny>>) -> PyResult<Option<PyObject>> {
    match obj {
        None => Ok(None), // If the object is None, return None
        Some(py_obj) => {

            let val = py_obj.bind(py);

            // If the object is already a UUID, return it immediately
            if val.get_type().name()? == "UUID" {
                return Ok(Some(py_obj.into()));  // Directly return the Py<PyAny> object
            }

            // Check if it's a pgproto.UUID (asyncpg's UUID)
            if val.get_type().name()? == "UUID" && val.hasattr("as_text")? {
                if let Ok(uuid_str) = val.call_method0("as_text")?.extract::<String>() {
                    if let Ok(parsed_uuid) = Uuid::parse_str(&uuid_str) {
                        return Ok(Some(python_uuid(py, parsed_uuid)?));
                    }
                }
            }

            // If the object is callable, call it and use its result
            if val.is_callable() {
                if let Ok(call_result) = val.call0() {
                    if let Ok(call_str) = call_result.str()?.to_str() {
                        if let Ok(parsed_uuid) = Uuid::parse_str(call_str) {
                            return Ok(Some(python_uuid(py, parsed_uuid)?));
                        }
                    }
                }
            }

            // Convert to string and try parsing as UUID
            if let Ok(obj_str) = val.str()?.to_str() {
                if let Ok(parsed_uuid) = Uuid::parse_str(obj_str) {
                    return Ok(Some(python_uuid(py, parsed_uuid)?));
                }
            }

            // If all attempts fail, return None
            Ok(None)
        }
    }
}

/// Helper function to create a Python `uuid.UUID` object from a Rust `Uuid`
fn python_uuid(py: Python, uuid_obj: Uuid) -> PyResult<PyObject> {
    let uuid_mod = py.import("uuid")?;
    let py_uuid = uuid_mod.getattr("UUID")?.call1((uuid_obj.to_string(),))?;
    Ok(py_uuid.into())
}

#[pyfunction]
#[pyo3(signature = (obj=None))]
fn to_uuid_str(py: Python, obj: Option<Py<PyAny>>) -> PyResult<Option<PyObject>> {
    match obj {
        None => Ok(None),  // If input is None, return None
        Some(py_obj) => {
            let val = py_obj.bind(py);

            // If it's already a UUID, return it directly (avoid conversion overhead)
            if val.get_type().name()? == "UUID" {
                return Ok(Some(py_obj.into()));  // ✅ Fastest path
            }

            // If it's callable, call it and use its result
            if val.is_callable() {
                let call_result = val.call0()?;  // ✅ Only call once
                return to_uuid(py, Some(call_result.extract()?));  // ✅ Recursively process result
            }

            // If it's a valid UUID string, return it as a string
            if let Ok(obj_str) = val.str()?.to_str() {
                if Uuid::parse_str(obj_str).is_ok() {
                    return Ok(Some(PyString::new(py, obj_str).into()));  // ✅ Let Python handle conversion
                }
            }

            // If all attempts fail, return None
            Ok(None)
        }
    }
}

#[pyfunction]
#[pyo3(signature = (obj=None))]
fn to_uuid(py: Python, obj: Option<Py<PyAny>>) -> PyResult<Option<PyObject>> {
    match obj {
        None => Ok(None),  // If input is None, return None
        Some(py_obj) => {
            let converters = py.import("datamodel.converters")?;  // Import Cython module
            let cython_uuid = converters.getattr("to_uuid")?;  // Get Cython function
            // Call Cython's to_uuid function and return its result
            let result = cython_uuid.call1((py_obj,))?;
            Ok(Some(result.into()))
        }
    }
}

#[pyfunction]
#[pyo3(signature = (obj=None))]
fn to_integer(py: Python, obj: Option<Py<PyAny>>) -> PyResult<Option<PyObject>> {
    match obj {
        None => Ok(None), // If input is None, return None
        Some(py_obj) => {
            // Bind the object to the current GIL.
            let val = py_obj.bind(py);

            // If the object is already an integer, return it directly.
            if val.is_instance(&PyInt::type_object(py))? {
                return Ok(Some(py_obj.into()));
            }

            // If the object is a string, attempt to parse it as an integer.
            if val.is_instance(&PyString::type_object(py))? {
                let py_str = val.downcast::<PyString>()?;
                if let Ok(parsed_int) = py_str.to_str()?.parse::<i64>() {
                    // Construct a new Python integer by calling the type.
                    let py_int_obj = py.get_type::<PyInt>().call1((parsed_int,))?;
                    return Ok(Some(py_int_obj.into()));
                } else {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Invalid integer string: {}", py_str.to_str()?),
                    ));
                }
            }

            // If it's callable, call it and recursively process its result.
            if val.is_callable() {
                let call_result = val.call0()?; // Call with no arguments.
                return to_integer(py, Some(call_result.extract()?));
            }

            // Try converting the object to an integer.
            match val.extract::<i64>() {
                Ok(int_value) => {
                    // Construct a Python int by calling the Python integer type.
                    let py_int_obj = py.get_type::<PyInt>().call1((int_value,))?;
                    Ok(Some(py_int_obj.into()))
                }
                Err(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid conversion to Integer of {}", val.str()?.to_str()?),
                )),
            }
        }
    }
}

#[pyfunction]
#[pyo3(signature = (obj=None))]
fn to_float(py: Python, obj: Option<Py<PyAny>>) -> PyResult<Option<PyObject>> {
    match obj {
        None => Ok(None), // If input is None, return None
        Some(py_obj) => {
            let val = py_obj.bind(py); // Bind the object to the Python GIL

            // If the object is already a float, return it directly.
            if val.get_type().name()? == "float" {
                return Ok(Some(py_obj.into()));
            }

            // If the object is a string, attempt to parse it as a float.
            if val.is_instance(&PyString::type_object(py))? {
                let py_str = val.downcast::<PyString>()?;
                if let Ok(parsed_float) = py_str.to_str()?.parse::<f64>() {
                    // Create a Python float from the Rust f64.
                    return Ok(Some(PyFloat::new(py, parsed_float).into()));
                } else {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Invalid float string: {}", py_str.to_str()?),
                    ));
                }
            }

            // If it's callable, call it and process its result recursively.
            if val.is_callable() {
                let call_result = val.call0()?; // Call the object with no arguments
                return to_float(py, Some(call_result.extract()?)); // Recursively process result
            }

            // Try converting the object to an f64.
            match val.extract::<f64>() {
                Ok(float_value) => Ok(Some(PyFloat::new(py, float_value).into())),
                Err(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid conversion to Float of {}", val.str()?.to_str()?),
                )),
            }
        }
    }
}


#[pyfunction]
#[pyo3(signature = (obj=None))]
fn to_decimal(py: Python, obj: Option<Py<PyAny>>) -> PyResult<Option<PyObject>> {
    match obj {
        None => Ok(None), // If input is None, return None
        Some(py_obj) => {
            let val = py_obj.bind(py); // Bind object in PyO3 0.23.0

            // If the object is already a Decimal, return it directly
            if val.get_type().name()? == "Decimal" {
                return Ok(Some(py_obj.into())); // ✅ Return existing Decimal
            }

            // Import Python's `decimal.Decimal`
            let py_decimal = py.import("decimal")?.getattr("Decimal")?;

            // If the object is a string, attempt to parse it as a Decimal
            if val.is_instance(&PyString::type_object(py))? {
                let py_str = val.downcast::<PyString>()?;
                if let Ok(parsed_decimal) = Decimal::from_str(py_str.to_str()?) {
                    return Ok(Some(py_decimal.call1((parsed_decimal.to_string(),))?.into())); // ✅ Convert Rust Decimal to Python Decimal
                } else {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Invalid decimal string: {}", py_str.to_str()?),
                    ));
                }
            }

            // If it's callable, call it and process its result
            if val.is_callable() {
                let call_result = val.call0()?; // Only call once
                return to_decimal(py, Some(call_result.extract()?)); // ✅ Recursively process result
            }

            // Try converting to a Decimal from a float
            match val.extract::<f64>() {
                Ok(float_value) => {
                    let rust_decimal = Decimal::from_f64_retain(float_value)
                        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Invalid conversion to Decimal from float: {}", float_value),
                        ))?;
                    return Ok(Some(py_decimal.call1((rust_decimal.to_string(),))?.into())); // ✅ Convert Rust Decimal to Python Decimal
                }
                Err(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid conversion to Decimal of {}", val.str()?.to_str()?),
                )),
            }
        }
    }
}

/// Python module declaration
#[pymodule]
fn rs_parsers(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(to_string, m)?)?;
    m.add_function(wrap_pyfunction!(strtobool, m)?)?;
    m.add_function(wrap_pyfunction!(to_boolean, m)?)?;
    m.add_function(wrap_pyfunction!(to_date, m)?)?;
    m.add_function(wrap_pyfunction!(to_datetime, m)?)?;
    m.add_function(wrap_pyfunction!(to_timestamp, m)?)?;
    m.add_function(wrap_pyfunction!(slugify_camelcase, m)?)?;
    m.add_function(wrap_pyfunction!(to_uuid_str, m)?)?;
    m.add_function(wrap_pyfunction!(to_uuid_obj, m)?)?;
    m.add_function(wrap_pyfunction!(to_uuid, m)?)?;
    m.add_function(wrap_pyfunction!(to_integer, m)?)?;
    m.add_function(wrap_pyfunction!(to_float, m)?)?;
    m.add_function(wrap_pyfunction!(to_decimal, m)?)?;
    m.add_function(wrap_pyfunction!(to_list, m)?)?;
    Ok(())
}
