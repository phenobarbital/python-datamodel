# Original request

python-datamodel borns as a drop-in replacement for dataclasses (used in ORM) several years ago when pydantic 1.x was worse in performance than python-datamodel, I leave untouched the code and pydantic 2.x migrated to Rust are faster than python-datamodel in 15x of magnitude: ```  benchmark                           total ms     avg ms  median ms    min ms    max ms       ops/sec
  ----------------------------------------------------------------------------------------------------
  BaseModel (raw str -> coerced)       397.777     0.0398     0.0385    0.0369    0.1399        25,140
  BaseModel (already-typed input)      315.839     0.0316     0.0308    0.0301    0.1190        31,662
  stdlib @dataclass (no checks)          4.983     0.0005     0.0005    0.0005    0.0279     2,006,908
  pydantic BaseModel (raw str)          26.169     0.0026     0.0025    0.0024    0.0541       382,135
  pydantic @dataclass (raw str)         43.074     0.0043     0.0041    0.0040    0.0618       232,158
  Employee.json() serialization        239.910     0.0240     0.0144    0.0127   43.7977        41,682
``` my concern is not creating a "replacement" of pydantic, but there is several codebase in company using python-datamodel and starts a migration to pydantic is not a case, but doing some refactor and copying some pydantic 2.x strategies around caching mechanisms, Rust usage and speed up performance can be useful, but the hard constraint is: we need to preserve the complete backward compatibility with current codebase.

## Follow-up

maybe one aggresive idea is migrating _validation_ to rust and executes the validation in parallel?
