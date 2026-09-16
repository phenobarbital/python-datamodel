#!/usr/bin/env python
"""Installed-wheel smoke test for Field, Column, and model construction.

Runs without pytest. Exits 0 on success, 1 on failure.
Prints interpreter, package version, and extension path for provenance.
"""
import sys


def main():
    print(f"Python: {sys.version}")

    import datamodel
    print(f"datamodel version: {datamodel.__version__}")
    print(f"datamodel path: {datamodel.__file__}")

    import datamodel.rs_parsers as r
    assert r.HAS_RUST, "Rust extension not available"
    print("HAS_RUST: OK")

    from datamodel import BaseModel, Field, Column

    f1 = Field()
    assert f1.doc is None, f"Field().doc should be None, got {f1.doc!r}"

    f2 = Field(doc="standalone")
    assert f2.doc == "standalone", f"Field(doc=...).doc mismatch: {f2.doc!r}"

    c = Column(doc="col doc")
    assert c.doc == "col doc", f"Column(doc=...).doc mismatch: {c.doc!r}"
    print("Field/Column doc: OK")

    class SmokeModel(BaseModel):
        __annotations__ = {"value": int}
        value = Column(default=0, doc="smoke value")

    model = SmokeModel(value="7")
    assert type(model.value) is int and model.value == 7, (
        f"Expected int 7, got {type(model.value).__name__} {model.value!r}"
    )
    assert "value" in SmokeModel.__columns__, "Field not in __columns__"
    assert SmokeModel.__columns__["value"].doc == "smoke value", (
        f"doc mismatch: {SmokeModel.__columns__['value'].doc!r}"
    )
    print("Model construction: OK")

    print("All smoke checks passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"SMOKE FAILED: {e}", file=sys.stderr)
        sys.exit(1)
