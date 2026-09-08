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
    // FEAT-2/TASK-17: sequential bounded executor (development-only).
    m.add_class::<NativePlan>()?;
    m.add("SUPPORTED_KINDS", ("str", "int", "float", "bool"))?;
    Ok(())
}

// ===========================================================================
// FEAT-2 / TASK-17 -- sequential, bounded, model-level native executor
// ===========================================================================
//
// EXPERIMENTAL AND DEVELOPMENT-ONLY. Nothing in `datamodel` imports this; the
// package's default loading and constructors are untouched. The benchmark
// harness (`benchmarks/native_validation.py`) loads the built cdylib
// explicitly by path.
//
// PRIVATE INTERFACE (consumed by TASK-18; verify against this file, do not
// infer it from names):
//
//   rs_core.SUPPORTED_KINDS -> tuple[str, ...]
//   rs_core.NativePlan(descriptors) -> plan
//       descriptors: sequence of (name, kind, min, max, min_len, max_len)
//           name     : str
//           kind     : one of SUPPORTED_KINDS
//           min, max : int | None   -- numeric bounds (int/float kinds)
//           min_len,
//           max_len  : int | None   -- string length bounds (str kind)
//   plan.eligible     -> bool   False if ANY descriptor kind is unsupported
//   plan.field_count  -> int
//   plan.kinds        -> list[str]
//   plan.execute(values: dict) -> list[(name, bool)] | None
//       None  => the row is INELIGIBLE; the caller MUST run the legacy Python
//                path. This is not a validation result.
//       list  => per-field validity in plan order.
//
// Design rules, all of them load-bearing:
//
// * Eligibility is decided in a FIRST PASS over every field, before any
//   validation result is produced, so a row can never be half-executed and
//   then handed back to Python -- the caller re-runs from a clean state and no
//   parser runs twice.
// * A field is never SKIPPED. Anything not provably handled makes the whole
//   row ineligible.
// * `int` values that do not fit i64 make the row ineligible rather than being
//   truncated or reported invalid: Python integers are arbitrary precision and
//   this executor must not narrow the accepted set. (The pre-existing
//   `validate_datamodel`/`parse_datamodel` prototypes in this file get this
//   wrong -- they report such a value as simply invalid. They are left alone
//   and are NOT on the exercised path.)
// * Subclass instances (including `bool` where `int` is expected, since
//   `bool` is a subclass of `int`) make the row ineligible: Python's
//   `valid_*` validators are isinstance-based and the exact semantics are
//   subtle, so the executor defers rather than guesses.
// * Temporal kinds are deliberately EXCLUDED from the supported set. The
//   prototype's `NaiveDate::parse_from_str(s, "%Y-%m-%d")` handling does not
//   reproduce Python's temporal variants, so those fields are ineligible
//   instead of being handled wrongly.
// * No `unwrap`, `expect` or panic on user-supplied data anywhere below.

use pyo3::types::{PyBool, PyFloat, PyInt, PyString, PyList, PyTuple};

#[derive(Clone, Copy, PartialEq, Debug)]
enum Kind {
    Str,
    Int,
    Float,
    Bool,
}

impl Kind {
    fn from_name(name: &str) -> Option<Kind> {
        match name {
            "str" => Some(Kind::Str),
            "int" => Some(Kind::Int),
            "float" => Some(Kind::Float),
            "bool" => Some(Kind::Bool),
            _ => None,
        }
    }

    fn name(&self) -> &'static str {
        match self {
            Kind::Str => "str",
            Kind::Int => "int",
            Kind::Float => "float",
            Kind::Bool => "bool",
        }
    }
}

#[derive(Clone)]
struct PlanField {
    name: String,
    kind: Kind,
    min: Option<i64>,
    max: Option<i64>,
    min_len: Option<usize>,
    max_len: Option<usize>,
}

/// Outcome of the eligibility pass for one field.
enum Eligibility {
    /// Exactly the expected type; carries the decided validity.
    Decided(bool),
    /// Anything we will not reason about: the whole row falls back.
    Ineligible,
}

/// A cached, immutable plan for one model's eligible scalar fields.
#[pyclass]
pub struct NativePlan {
    fields: Vec<PlanField>,
    eligible: bool,
    /// Bounded, REUSABLE worker pool. Built once per plan, never unbounded,
    /// and only used while the GIL is released. `None` means this plan runs
    /// sequentially only.
    pool: Option<Arc<ThreadPool>>,
}

#[pymethods]
impl NativePlan {
    #[new]
    #[pyo3(signature = (descriptors, threads=None))]
    fn new(descriptors: &Bound<'_, PyAny>, threads: Option<usize>) -> PyResult<Self> {
        let mut fields: Vec<PlanField> = Vec::new();
        let mut eligible = true;

        let items = descriptors.try_iter()?;
        for item in items {
            let item = item?;
            let tuple = item.cast_into::<PyTuple>().map_err(|_| {
                PyTypeError::new_err("each descriptor must be a tuple")
            })?;
            if tuple.len() != 6 {
                return Err(PyTypeError::new_err(
                    "each descriptor must be (name, kind, min, max, min_len, max_len)",
                ));
            }
            let name: String = tuple.get_item(0)?.extract()?;
            let kind_name: String = tuple.get_item(1)?.extract()?;
            let min: Option<i64> = tuple.get_item(2)?.extract()?;
            let max: Option<i64> = tuple.get_item(3)?.extract()?;
            let min_len: Option<usize> = tuple.get_item(4)?.extract()?;
            let max_len: Option<usize> = tuple.get_item(5)?.extract()?;

            match Kind::from_name(&kind_name) {
                Some(kind) => fields.push(PlanField {
                    name,
                    kind,
                    min,
                    max,
                    min_len,
                    max_len,
                }),
                None => {
                    // An unsupported kind does not merely skip that field: the
                    // whole plan becomes ineligible, so no caller can end up
                    // validating a subset and believing it validated the model.
                    eligible = false;
                }
            }
        }

        // A bounded pool, built once and reused. Never unbounded: a caller
        // asking for 0 threads gets sequential execution rather than Rayon's
        // "one per core" default.
        let pool = match threads {
            Some(count) if count > 0 => Some(Arc::new(
                rayon::ThreadPoolBuilder::new()
                    .num_threads(count)
                    .build()
                    .map_err(|err| PyTypeError::new_err(format!(
                        "could not build a bounded worker pool: {err}"
                    )))?,
            )),
            _ => None,
        };

        Ok(NativePlan { fields, eligible, pool })
    }

    #[getter]
    fn eligible(&self) -> bool {
        self.eligible
    }

    #[getter]
    fn field_count(&self) -> usize {
        self.fields.len()
    }

    #[getter]
    fn kinds(&self) -> Vec<String> {
        self.fields.iter().map(|f| f.kind.name().to_string()).collect()
    }

    /// Validate one row. Returns None when the caller must use the legacy path.
    fn execute<'py>(
        &self,
        py: Python<'py>,
        values: &Bound<'py, PyDict>,
    ) -> PyResult<Option<Py<PyList>>> {
        if !self.eligible {
            return Ok(None);
        }

        // ---- PASS 1: eligibility only. No results are produced or kept. ----
        let mut decided: Vec<bool> = Vec::with_capacity(self.fields.len());
        for field in &self.fields {
            let item = values.get_item(field.name.as_str())?;
            let value = match item {
                Some(value) => value,
                // A missing key means presence/default handling, which this
                // executor does not implement. Fall back.
                None => return Ok(None),
            };
            match self.check(&value, field)? {
                Eligibility::Ineligible => return Ok(None),
                Eligibility::Decided(ok) => decided.push(ok),
            }
        }

        // ---- PASS 2: publish. Cannot fail; every field is already decided. --
        let out = PyList::empty(py);
        for (field, ok) in self.fields.iter().zip(decided.into_iter()) {
            let pair = PyTuple::new(py, &[
                field.name.clone().into_pyobject(py)?.into_any(),
                ok.into_pyobject(py)?.to_owned().into_any(),
            ])?;
            out.append(pair)?;
        }
        Ok(Some(out.unbind()))
    }

    /// Number of worker threads this plan's bounded pool was built with.
    #[getter]
    fn threads(&self) -> usize {
        match &self.pool {
            Some(pool) => pool.current_num_threads(),
            None => 0,
        }
    }

    /// Validate many rows, optionally in bounded parallel.
    ///
    /// Returns one entry per row IN ORDER: either the per-field results, or
    /// `None` for a row that must be run serially by the caller.
    #[pyo3(signature = (rows, parallel=false))]
    fn execute_batch<'py>(
        &self,
        py: Python<'py>,
        rows: &Bound<'py, PyAny>,
        parallel: bool,
    ) -> PyResult<Py<PyList>> {
        if !self.eligible {
            let out = PyList::empty(py);
            for _ in rows.try_iter()? {
                out.append(py.None())?;
            }
            return Ok(out.unbind());
        }

        // ---- PHASE 1: SNAPSHOT (GIL held) -----------------------------------
        let mut snapshots: Vec<Option<Vec<Owned>>> = Vec::new();
        for row in rows.try_iter()? {
            let row = row?;
            let dict = row.cast_into::<PyDict>().map_err(|_| {
                PyTypeError::new_err("each row must be a dict")
            })?;
            snapshots.push(self.snapshot_row(&dict)?);
        }

        // ---- PHASE 2: DETACH (no Python reachable from here) ----------------
        let use_parallel = parallel && self.pool.is_some();
        let computed: Vec<Option<Vec<bool>>> = if use_parallel {
            let pool = match &self.pool {
                Some(pool) => Arc::clone(pool),
                None => unreachable!("guarded by use_parallel"),
            };
            py.detach(|| {
                pool.install(|| {
                    snapshots
                        .par_iter()
                        .map(|snapshot| {
                            snapshot.as_ref().map(|row| self.validate_owned(row))
                        })
                        .collect()
                })
            })
        } else {
            py.detach(|| {
                snapshots
                    .iter()
                    .map(|snapshot| snapshot.as_ref().map(|row| self.validate_owned(row)))
                    .collect()
            })
        };

        // ---- PHASE 3: REBUILD (GIL held, original order) --------------------
        let out = PyList::empty(py);
        for entry in computed {
            match entry {
                None => out.append(py.None())?,
                Some(flags) => {
                    let row_out = PyList::empty(py);
                    for (field, ok) in self.fields.iter().zip(flags.into_iter()) {
                        let pair = PyTuple::new(py, &[
                            field.name.clone().into_pyobject(py)?.into_any(),
                            ok.into_pyobject(py)?.to_owned().into_any(),
                        ])?;
                        row_out.append(pair)?;
                    }
                    out.append(row_out)?;
                }
            }
        }
        Ok(out.unbind())
    }
}

impl NativePlan {
    fn check(&self, value: &Bound<'_, PyAny>, field: &PlanField) -> PyResult<Eligibility> {
        match field.kind {
            Kind::Bool => {
                if value.is_exact_instance_of::<PyBool>() {
                    Ok(Eligibility::Decided(true))
                } else if value.is_instance_of::<PyBool>() {
                    Ok(Eligibility::Ineligible)
                } else {
                    Ok(Eligibility::Decided(false))
                }
            }
            Kind::Int => {
                // `bool` is a subclass of `int`; Python's valid_int accepts it
                // via isinstance. Defer rather than encode that subtlety here.
                if value.is_instance_of::<PyBool>() {
                    return Ok(Eligibility::Ineligible);
                }
                if !value.is_exact_instance_of::<PyInt>() {
                    return Ok(if value.is_instance_of::<PyInt>() {
                        Eligibility::Ineligible // int subclass
                    } else {
                        Eligibility::Decided(false)
                    });
                }
                // Arbitrary-precision guard: never truncate, never call it
                // invalid -- hand the row back to Python.
                let native: i64 = match value.extract::<i64>() {
                    Ok(native) => native,
                    Err(_) => return Ok(Eligibility::Ineligible),
                };
                if let Some(min) = field.min {
                    if native < min {
                        return Ok(Eligibility::Decided(false));
                    }
                }
                if let Some(max) = field.max {
                    if native > max {
                        return Ok(Eligibility::Decided(false));
                    }
                }
                Ok(Eligibility::Decided(true))
            }
            Kind::Float => {
                if value.is_instance_of::<PyBool>() {
                    return Ok(Eligibility::Ineligible);
                }
                if value.is_exact_instance_of::<PyFloat>() {
                    let native: f64 = match value.extract::<f64>() {
                        Ok(native) => native,
                        Err(_) => return Ok(Eligibility::Ineligible),
                    };
                    if let Some(min) = field.min {
                        if native < min as f64 {
                            return Ok(Eligibility::Decided(false));
                        }
                    }
                    if let Some(max) = field.max {
                        if native > max as f64 {
                            return Ok(Eligibility::Decided(false));
                        }
                    }
                    return Ok(Eligibility::Decided(true));
                }
                // Python's valid_float accepts an int too, but the exact
                // int-vs-float constraint semantics are not worth guessing.
                if value.is_instance_of::<PyInt>() {
                    return Ok(Eligibility::Ineligible);
                }
                Ok(Eligibility::Decided(false))
            }
            Kind::Str => {
                if !value.is_exact_instance_of::<PyString>() {
                    return Ok(if value.is_instance_of::<PyString>() {
                        Eligibility::Ineligible // str subclass
                    } else {
                        Eligibility::Decided(false)
                    });
                }
                let text = match value.extract::<String>() {
                    Ok(text) => text,
                    Err(_) => return Ok(Eligibility::Ineligible),
                };
                // Count CHARACTERS, matching Python's len() on str, not bytes.
                let length = text.chars().count();
                if let Some(min_len) = field.min_len {
                    if length < min_len {
                        return Ok(Eligibility::Decided(false));
                    }
                }
                if let Some(max_len) = field.max_len {
                    if length > max_len {
                        return Ok(Eligibility::Decided(false));
                    }
                }
                Ok(Eligibility::Decided(true))
            }
        }
    }
}

// ===========================================================================
// FEAT-2 / TASK-19 -- bounded parallel snapshot execution (development-only)
// ===========================================================================
//
// The rule that makes this safe: **no worker touches Python.**
//
// Execution is in three strictly separated phases:
//
//   1. SNAPSHOT (GIL held).  Every row is converted into owned Rust values, or
//      marked ineligible. Nothing is validated yet.
//   2. DETACH (GIL released via `Python::detach`).  Workers operate only on
//      the owned snapshot inside a bounded, reusable Rayon pool. There is no
//      `Py<...>`, no `Bound<...>` and no callback reachable from here, so a
//      worker cannot touch the interpreter even by accident, and the caller is
//      not required to hold the GIL on anyone's behalf.
//   3. REBUILD (GIL re-acquired).  Results are turned back into Python objects
//      in the ORIGINAL row order.
//
// Ordering is deterministic: `par_iter().collect()` into a `Vec` preserves
// index order regardless of completion order, and ineligible rows keep their
// slot as `None` so the caller can run exactly those serially.
//
// Ineligible rows are never executed natively and never reordered. Custom
// callbacks, errors, descriptors and mutations all remain on the serial
// Python path -- this executor still only validates.

use std::sync::Arc;
use rayon::ThreadPool;

/// An owned, Python-free snapshot of one field value.
#[derive(Clone, Debug)]
enum Owned {
    Str(String),
    Int(i64),
    Float(f64),
    Bool(bool),
    /// Present, but definitively the wrong type: decided without Python.
    WrongType,
}

impl NativePlan {
    /// Snapshot one row into owned values. `None` means ineligible.
    ///
    /// Runs with the GIL held. Every Python interaction happens here and
    /// nowhere else.
    fn snapshot_row(&self, values: &Bound<'_, PyDict>) -> PyResult<Option<Vec<Owned>>> {
        let mut owned: Vec<Owned> = Vec::with_capacity(self.fields.len());
        for field in &self.fields {
            let item = values.get_item(field.name.as_str())?;
            let value = match item {
                Some(value) => value,
                None => return Ok(None),
            };
            let snapshot = match field.kind {
                Kind::Bool => {
                    if value.is_exact_instance_of::<PyBool>() {
                        match value.extract::<bool>() {
                            Ok(native) => Owned::Bool(native),
                            Err(_) => return Ok(None),
                        }
                    } else if value.is_instance_of::<PyBool>() {
                        return Ok(None);
                    } else {
                        Owned::WrongType
                    }
                }
                Kind::Int => {
                    if value.is_instance_of::<PyBool>() {
                        return Ok(None);
                    }
                    if value.is_exact_instance_of::<PyInt>() {
                        match value.extract::<i64>() {
                            Ok(native) => Owned::Int(native),
                            // Arbitrary precision: never truncate.
                            Err(_) => return Ok(None),
                        }
                    } else if value.is_instance_of::<PyInt>() {
                        return Ok(None);
                    } else {
                        Owned::WrongType
                    }
                }
                Kind::Float => {
                    if value.is_instance_of::<PyBool>() {
                        return Ok(None);
                    }
                    if value.is_exact_instance_of::<PyFloat>() {
                        match value.extract::<f64>() {
                            Ok(native) => Owned::Float(native),
                            Err(_) => return Ok(None),
                        }
                    } else if value.is_instance_of::<PyInt>() {
                        return Ok(None);
                    } else {
                        Owned::WrongType
                    }
                }
                Kind::Str => {
                    if value.is_exact_instance_of::<PyString>() {
                        match value.extract::<String>() {
                            Ok(text) => Owned::Str(text),
                            Err(_) => return Ok(None),
                        }
                    } else if value.is_instance_of::<PyString>() {
                        return Ok(None);
                    } else {
                        Owned::WrongType
                    }
                }
            };
            owned.push(snapshot);
        }
        Ok(Some(owned))
    }

    /// Validate an owned snapshot. Pure Rust: callable with the GIL released.
    fn validate_owned(&self, row: &[Owned]) -> Vec<bool> {
        let mut out = Vec::with_capacity(row.len());
        for (field, value) in self.fields.iter().zip(row.iter()) {
            out.push(match value {
                Owned::WrongType => false,
                Owned::Bool(_) => true,
                Owned::Int(native) => {
                    let mut ok = true;
                    if let Some(min) = field.min {
                        if *native < min {
                            ok = false;
                        }
                    }
                    if let Some(max) = field.max {
                        if *native > max {
                            ok = false;
                        }
                    }
                    ok
                }
                Owned::Float(native) => {
                    let mut ok = true;
                    if let Some(min) = field.min {
                        if *native < min as f64 {
                            ok = false;
                        }
                    }
                    if let Some(max) = field.max {
                        if *native > max as f64 {
                            ok = false;
                        }
                    }
                    ok
                }
                Owned::Str(text) => {
                    let length = text.chars().count();
                    let mut ok = true;
                    if let Some(min_len) = field.min_len {
                        if length < min_len {
                            ok = false;
                        }
                    }
                    if let Some(max_len) = field.max_len {
                        if length > max_len {
                            ok = false;
                        }
                    }
                    ok
                }
            });
        }
        out
    }
}
