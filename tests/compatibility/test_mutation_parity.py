"""Adversarial mutation parity for the validation gate (FEAT-2 / TASK-14).

TASK-13 made ``processing_fields`` skip the generic ``_validation_`` dispatch
for exactly-typed supported scalars.  That gate reads a *precomputed* policy,
so the interesting failures are all of one shape: **something changes after the
policy was built, and the gate does not notice.**

This module attacks that surface directly -- replacing metadata mappings,
setting a constraint to ``None`` versus deleting it, swapping parsers,
validators, types and ``Meta``, and replacing fields dynamically.

Why these tests cannot merely mirror the implementation
=======================================================

Every scenario is executed **twice, in two separate processes**: once against
the rebuilt 0.10.21 engineering reference and once against the candidate, each
bound to its own compiled artifacts.  The assertion is that the two agree.  A
test written to match whatever the gate happens to do would fail the moment the
reference disagreed, so the oracle is the reference build -- not this file's
expectations, and not mine.

``test_the_comparison_detects_an_intentionally_altered_gate`` closes the loop
by running a scenario whose result is deliberately corrupted and asserting the
comparison reports it.  Without that, "no divergences" could just mean the
comparison is blind.

Shared harness
==============

:func:`run_scenarios` and :func:`assert_parity` live here and are imported by
``test_hook_parity.py`` and ``test_generic_fallback.py``.  All three files are
owned by this task.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.compatibility.observations import compare  # noqa: E402
from tests.compatibility.runner import (  # noqa: E402
    candidate_environment,
    reference_environment,
)

HARNESS_ROOT = Path(__file__).resolve().parents[2]
CHILD_TIMEOUT_SECONDS = 300

REFERENCE_MISSING = (
    "the reference worktree is not built, so mutation parity could not be "
    "checked. A SKIPPED comparison is NOT a passing comparison."
)

_CHILD = r'''
import json, re, sys, traceback
from pathlib import Path

request = json.loads(sys.stdin.read())
expect_root = Path(request["expect_root"]).resolve()
harness_root = Path(request["harness_root"]).resolve()

# 1. Bind `datamodel` from THIS environment before anything else can.
sys.path.insert(0, str(expect_root))
import datamodel
loaded = Path(datamodel.__file__).resolve()
if expect_root not in loaded.parents:
    raise SystemExit("imported datamodel from %s, not under %s" % (loaded, expect_root))
# 2. Only now make the shared harness importable.
while str(expect_root) in sys.path:
    sys.path.remove(str(expect_root))
sys.path.insert(0, str(harness_root))

_ADDR = re.compile(r"0x[0-9a-fA-F]+")


def _strip(text):
    return _ADDR.sub("0xADDR", text)


def describe(value, depth=0):
    """A deterministic, JSON-safe description of anything."""
    if depth > 6:
        return {"t": "...", "v": "<deep>"}
    if value is None or isinstance(value, (bool, int, str)):
        return {"t": type(value).__name__, "v": value}
    if isinstance(value, float):
        return {"t": "float", "v": repr(value)}
    if isinstance(value, (list, tuple)):
        return {"t": type(value).__name__,
                "v": [describe(item, depth + 1) for item in value]}
    if isinstance(value, (set, frozenset)):
        return {"t": type(value).__name__,
                "v": sorted(_strip(repr(item)) for item in value)}
    if isinstance(value, dict):
        return {"t": "dict",
                "v": [[describe(k, depth + 1), describe(v, depth + 1)]
                      for k, v in value.items()]}
    if isinstance(value, type):
        return {"t": "type", "v": value.__name__}
    return {"t": type(value).__name__, "v": _strip(repr(value))}


def attempt(fn):
    """Run `fn`, describing either its result or the exception it raised."""
    try:
        return {"outcome": "ok", "value": describe(fn())}
    except BaseException as exc:
        return {"outcome": "error",
                "type": type(exc).__name__,
                "message": _strip(str(exc)),
                "payload": describe(getattr(exc, "payload", None))}


namespace = {
    "describe": describe, "attempt": attempt, "datamodel": datamodel,
}
exec("from datamodel import BaseModel, Column, Field", namespace)
exec("from datamodel.exceptions import ValidationError", namespace)

results = {}
for name, source in request["scenarios"].items():
    local = dict(namespace)
    try:
        exec(source, local)
        results[name] = local["run"]()
    except BaseException as exc:
        results[name] = {"scenario_error": type(exc).__name__,
                         "message": _strip(str(exc)),
                         "trace": _strip(traceback.format_exc())[-1500:]}
print(json.dumps({"results": results,
                  "version": datamodel.version.__version__,
                  "datamodel_file": str(loaded)}))
'''


def _run_in(environment, scenarios):
    environment.validate()
    completed = subprocess.run(
        [str(environment.python), "-c", _CHILD],
        input=json.dumps({
            "expect_root": str(environment.root),
            "harness_root": str(HARNESS_ROOT),
            "scenarios": scenarios,
        }),
        capture_output=True, text=True, cwd=str(environment.root),
        env={"PATH": "/usr/bin:/bin", "PYTHONNOUSERSITE": "1",
             "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
             "HOME": str(Path.home())},
        timeout=CHILD_TIMEOUT_SECONDS, check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"{environment.name}: child exited {completed.returncode}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return json.loads(completed.stdout)


def run_scenarios(scenarios):
    """Execute `scenarios` in both builds. Returns (reference, candidate)."""
    reference = reference_environment()
    if reference is None:
        pytest.skip(REFERENCE_MISSING)
    return _run_in(reference, scenarios), _run_in(candidate_environment(), scenarios)


def assert_parity(scenarios):
    """Both builds must produce identical observations for every scenario."""
    reference, candidate = run_scenarios(scenarios)
    assert reference["version"] != candidate["version"], (
        "both runs loaded the same build; the comparison would be vacuous"
    )
    for name in scenarios:
        assert "scenario_error" not in reference["results"][name], (
            f"{name} failed to execute on the reference: "
            f"{reference['results'][name]}"
        )
    divergences = compare(reference["results"], candidate["results"])
    assert not divergences, "\n".join(d.describe() for d in divergences[:25])
    return reference, candidate


# ===========================================================================
# Scenarios: metadata and backing-map mutation
# ===========================================================================

METADATA_SCENARIOS = {
    # Replacing the whole backing map after the policy was built.
    "replace_backing_map": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    field = M.__columns__["v"]
    before = attempt(lambda: M(v=99).v)
    field._meta = dict(field._meta)
    field._meta["max"] = 10
    field.metadata = field._meta
    after = attempt(lambda: (M(v=99).get_errors() or {}))
    return {"before": before, "after": after}
''',
    # A constraint explicitly set to None must behave as absent, not as 0.
    "constraint_set_to_none_versus_removed": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False, max=10)
        class Meta:
            strict = False
    field = M.__columns__["v"]
    enforced = attempt(lambda: (M(v=99).get_errors() or {}))
    field._meta["max"] = None
    field.metadata = field._meta
    set_to_none = attempt(lambda: (M(v=99).get_errors() or {}))
    field._meta.pop("max", None)
    field.metadata = field._meta
    removed = attempt(lambda: (M(v=99).get_errors() or {}))
    return {"enforced": enforced, "set_to_none": set_to_none,
            "removed": removed}
''',
    # Zero is a real bound, not "absent".
    "zero_valued_constraint_is_not_absent": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False, min=0)
        class Meta:
            strict = False
    return {"negative": attempt(lambda: (M(v=-5).get_errors() or {})),
            "zero": attempt(lambda: (M(v=0).get_errors() or {})),
            "positive": attempt(lambda: (M(v=5).get_errors() or {}))}
''',
    "constraint_added_then_removed": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    field = M.__columns__["v"]
    steps = [attempt(lambda: (M(v=99).get_errors() or {}))]
    field._meta["max"] = 10
    field.metadata = field._meta
    steps.append(attempt(lambda: (M(v=99).get_errors() or {})))
    field._meta.pop("max")
    field.metadata = field._meta
    steps.append(attempt(lambda: (M(v=99).get_errors() or {})))
    return {"steps": steps}
''',
    "string_constraints_mutated": '''
def run():
    class M(BaseModel):
        s: str = Column(required=False)
        class Meta:
            strict = False
    field = M.__columns__["s"]
    out = {"initial": attempt(lambda: (M(s="abcdefghij").get_errors() or {}))}
    field._meta["max_length"] = 3
    field.metadata = field._meta
    out["max_length"] = attempt(lambda: (M(s="abcdefghij").get_errors() or {}))
    field._meta["min_length"] = 8
    field.metadata = field._meta
    out["min_length"] = attempt(lambda: (M(s="ab").get_errors() or {}))
    return out
''',
}

IDENTITY_SCENARIOS = {
    "validator_replaced": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    field = M.__columns__["v"]
    calls = []
    def rejecting(f, name, value, _type):
        calls.append(value)
        return "replacement says no"
    field.validator = rejecting
    result = attempt(lambda: (M(v=5).get_errors() or {}))
    return {"result": result, "calls": describe(calls)}
''',
    "validator_cleared": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    M.__columns__["v"].validator = None
    return {"valid": attempt(lambda: M(v=5).v),
            "invalid": attempt(lambda: (M(v="nope").get_errors() or {}))}
''',
    "parser_replaced": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    calls = []
    def parser(value):
        calls.append(value)
        return 1234
    M.__columns__["v"].parser = parser
    result = attempt(lambda: M(v=5).v)
    return {"result": result, "calls": describe(calls)}
''',
    "field_type_replaced": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    M.__columns__["v"].type = str
    return {"int_value": attempt(lambda: M(v=5).v),
            "str_value": attempt(lambda: M(v="x").v)}
''',
    "meta_strict_flipped_after_creation": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False, max=10)
        class Meta:
            strict = False
    loose = attempt(lambda: (M(v=99).get_errors() or {}))
    M.Meta.strict = True
    strict = attempt(lambda: M(v=99))
    M.Meta.strict = False
    return {"loose": loose, "strict": strict}
''',
    "dynamic_field_replacement": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    original = M.__columns__["v"]
    replacement = Field(required=False, default=None)
    replacement.name = "v"
    replacement.type = str
    M.__columns__["v"] = replacement
    M.__dataclass_fields__["v"] = replacement
    result = attempt(lambda: M(v="text").v)
    M.__columns__["v"] = original
    M.__dataclass_fields__["v"] = original
    return {"result": result}
''',
}

SUBCLASS_SCENARIOS = {
    "str_and_int_subclasses": '''
def run():
    class MyStr(str):
        pass
    class MyInt(int):
        pass
    class M(BaseModel):
        s: str = Column(required=False)
        i: int = Column(required=False)
        class Meta:
            strict = False
    return {"str_subclass": attempt(lambda: (M(s=MyStr("x")).get_errors() or {})),
            "int_subclass": attempt(lambda: M(i=MyInt(5)).i),
            "bool_as_int": attempt(lambda: M(i=True).i),
            "int_as_bool_field": attempt(lambda: M(s="ok").s)}
''',
    "boundary_values": '''
def run():
    class M(BaseModel):
        i: int = Column(required=False)
        s: str = Column(required=False)
        f: float = Column(required=False)
        class Meta:
            strict = False
    return {"zero": attempt(lambda: M(i=0).i),
            "false": attempt(lambda: M(i=False).i),
            "empty_string": attempt(lambda: M(s="").s),
            "zero_float": attempt(lambda: M(f=0.0).f),
            "huge_int": attempt(lambda: M(i=2**96).i),
            "negative": attempt(lambda: M(i=-1).i)}
''',
}


# ===========================================================================
# Tests
# ===========================================================================


def test_metadata_mutation_parity():
    """AC4: live metadata changes must behave identically on both builds."""
    assert_parity(METADATA_SCENARIOS)


def test_identity_replacement_parity():
    """A swapped parser/validator/type/Meta must not be silently ignored."""
    assert_parity(IDENTITY_SCENARIOS)


def test_subclass_and_boundary_parity():
    """Exact-type guards must not change subclass or boundary behaviour."""
    assert_parity(SUBCLASS_SCENARIOS)


def test_strict_and_non_strict_agree():
    """Both strict modes are compared, per the acceptance criteria."""
    scenarios = {
        "strict_raises": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False, max=10)
        class Meta:
            strict = True
    return {"valid": attempt(lambda: M(v=5).v),
            "invalid": attempt(lambda: M(v=99))}
''',
        "non_strict_accumulates": '''
def run():
    class M(BaseModel):
        a: int = Column(required=False, max=10)
        b: int = Column(required=False, max=10)
        c: str = Column(required=False, max_length=2)
        class Meta:
            strict = False
    instance = M(a=99, b=99, c="toolong")
    return {"errors": describe(sorted(instance.get_errors() or {})),
            "values": attempt(lambda: instance.to_dict())}
''',
    }
    assert_parity(scenarios)


def test_policy_is_invisible_on_both_builds():
    """AC7: no policy data may reach any externally observable output."""
    scenarios = {
        "observable_surface": '''
def run():
    class M(BaseModel):
        a: int = Column(required=False, default=1)
        b: str = Column(required=False, default="x")
    instance = M()
    return {
        "fields": describe(sorted(M.__fields__)),
        "columns": describe(sorted(M.__columns__)),
        "dataclass_fields": describe(sorted(M.__dataclass_fields__)),
        "to_dict_keys": describe(sorted(instance.to_dict())),
        "json": describe(instance.json()),
        "metadata_keys": describe(
            sorted({k for f in M.__columns__.values() for k in dict(f.metadata)})
        ),
    }
''',
    }
    reference, candidate = assert_parity(scenarios)
    rendered = json.dumps(candidate["results"])
    assert "_policy" not in rendered
    assert "FieldPolicy" not in rendered


def test_the_comparison_detects_an_intentionally_altered_gate():
    """The parity check must be able to FAIL, or it proves nothing.

    A scenario whose observation is deliberately corrupted stands in for a
    gate that quietly stopped enforcing a constraint. If `compare` reported
    nothing here, every other "parity holds" result in this file would be
    worthless.
    """
    scenarios = {
        "constraint_enforced": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False, max=10)
        class Meta:
            strict = False
    return {"violation": attempt(lambda: (M(v=99).get_errors() or {}))}
''',
    }
    reference, candidate = run_scenarios(scenarios)

    # Stand-in for a gate that skipped the constraint: the violation vanishes.
    broken = json.loads(json.dumps(candidate["results"]))
    broken["constraint_enforced"]["violation"] = {
        "outcome": "ok", "value": {"t": "dict", "v": []}
    }
    divergences = compare(reference["results"], broken)
    assert divergences, (
        "a scenario whose constraint stopped being enforced produced no "
        "divergence; the parity comparison is blind"
    )


def test_both_environments_are_really_different_builds():
    scenarios = {"trivial": '''
def run():
    return {"ok": True}
'''}
    reference, candidate = run_scenarios(scenarios)
    assert reference["version"] == "0.10.21"
    assert reference["datamodel_file"] != candidate["datamodel_file"]
