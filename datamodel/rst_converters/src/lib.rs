use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use pyo3::types::PyAny;
use pyo3::wrap_pyfunction;
use pyo3::types::{PyDate, PyDateTime};
use chrono::{Datelike, Timelike, NaiveDate, NaiveDateTime, DateTime, Utc};
use speedate::Date as SpeeDate;
use speedate::DateTime as SpeeDateTime;
// use speedate::{Date, DateTime, ParseError};

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
                let result = val.call0();
                match result {
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
    let naive_dt = NaiveDateTime::from_timestamp(seconds, microseconds);
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

    // Try parsing as ISO 8601 date only.
    for &fmt in &formats {
        if let Ok(date) = NaiveDate::parse_from_str(input, fmt) {
            return Ok(PyDate::new(py, date.year(), date.month() as u8, date.day() as u8)?.into_py(py));
        }
        if let Ok(date) = NaiveDate::parse_from_str(input, fmt) {
            // Convert NaiveDate to PyDate
            return Ok(PyDate::new(py, date.year(), date.month() as u8, date.day() as u8)?.into_py(py));
        }
    }

    // If all attempts fail, raise a ValueError.
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


/// Python module declaration
#[pymodule]
fn rst_converters(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(strtobool, m)?)?;
    m.add_function(wrap_pyfunction!(to_boolean, m)?)?;
    m.add_function(wrap_pyfunction!(to_date, m)?)?;
    m.add_function(wrap_pyfunction!(to_datetime, m)?)?;
    m.add_function(wrap_pyfunction!(to_timestamp, m)?)?;
    Ok(())
}
