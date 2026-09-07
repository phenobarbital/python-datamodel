"""Guards for the FEAT-2 compatibility corpus (TASK-7).

These tests do **not** assert what ``datamodel`` should do — that is the
differential runner's job, with the reference build as the oracle.  They assert
that the corpus itself is trustworthy:

* the ported ``Employee`` still has all eleven declarations, its defaults and
  its ``age`` bounds;
* no case can leak a mutation, a class-cache collision or a callback log into
  another case;
* the ``examples/`` coverage manifest accounts for every inventoried schema
  example, with an explicit reason wherever we adapted instead of imported.
"""
from __future__ import annotations

import ast
import json
import uuid
import warnings
from dataclasses import MISSING, fields as dc_fields
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from datamodel.rs_parsers import HAS_RUST

from tests.fixtures.model_performance import cases as cases_mod
from tests.fixtures.model_performance import models as models_mod
from tests.fixtures.model_performance.cases import (
    CASES,
    CASES_BY_NAME,
    EXPECT_ERROR,
    EXPECT_OK,
    build_kwargs,
    resolve_path,
)
from tests.fixtures.model_performance.models import (
    ALL_MODELS,
    EMPLOYEE_FIELD_SPEC,
    PROVENANCE,
    Employee,
)

RUST_SKIP_REASON = (
    "the rs_parsers extension is absent, so converters.pyx:199,236 cannot "
    "dereference rc.to_date/rc.to_datetime; this gap exists identically at the "
    "engineering reference and is recorded, not worked around"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = REPO_ROOT / "examples"
MANIFEST_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "model_performance" / "examples_manifest.json"
)


# ---------------------------------------------------------------------------
# examples/ inventory
# ---------------------------------------------------------------------------


def _is_main_guard(node: ast.stmt) -> bool:
    """True for ``if __name__ == "__main__":``."""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
    )


def _contains_call(node: ast.AST) -> bool:
    return any(isinstance(child, ast.Call) for child in ast.walk(node))


def _module_executes_at_import(tree: ast.Module) -> bool:
    """Would importing this module run more than declarations?

    Anything guarded by ``if __name__ == "__main__"`` does not count, and neither
    do imports, class/function definitions or literal assignments.  A
    module-level call *does* count -- that is precisely the hazard the corpus
    avoids by re-declaring schemas instead of importing them.
    """
    for node in tree.body:
        if isinstance(
            node,
            (ast.Import, ast.ImportFrom, ast.ClassDef,
             ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # docstring
        if _is_main_guard(node):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            if node.value is not None and _contains_call(node.value):
                return True
            continue
        if isinstance(node, (ast.Try, ast.With, ast.AsyncWith, ast.For,
                             ast.AsyncFor, ast.While, ast.If, ast.Expr,
                             ast.Raise, ast.Assert)):
            return True
    return False


def _model_bases(node: ast.ClassDef) -> list:
    names = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def _declared_models(tree: ast.Module) -> list:
    """Class names deriving (directly) from a datamodel base class."""
    known = {"BaseModel", "ModelMixin", "Model"}
    found = []
    local = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = set(_model_bases(node))
            if bases & known or bases & local:
                found.append(node.name)
                local.add(node.name)
    return found


def _parse(path: Path) -> ast.Module:
    """Parse without importing, and without letting a legacy ``SyntaxWarning``
    (several examples contain un-escaped regex literals) escape as an error
    under this project's ``filterwarnings = ["error"]`` setting."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def inventory_examples() -> dict:
    """AST-only inventory of ``examples/`` -- never imports anything."""
    inventory = {}
    for path in sorted(EXAMPLES_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            tree = _parse(path)
        except SyntaxError:  # pragma: no cover - defensive
            inventory[rel] = {"schema_bearing": False, "models": [],
                              "executes_at_import": True, "unparsable": True}
            continue
        models = _declared_models(tree)
        inventory[rel] = {
            "schema_bearing": bool(models),
            "models": models,
            "executes_at_import": _module_executes_at_import(tree),
        }
    return inventory


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Employee fidelity
# ---------------------------------------------------------------------------


def test_employee_preserves_all_eleven_declarations():
    """AC: 'Employee preserves all 11 declarations, defaults and constraints'."""
    names = tuple(f.name for f in dc_fields(Employee))
    assert names == tuple(name for name, _ in EMPLOYEE_FIELD_SPEC)
    assert len(names) == 11


def test_employee_defaults_match_the_source_example():
    by_name = {f.name: f for f in dc_fields(Employee)}

    assert by_name["email"].default == ''
    assert by_name["rating"].default == 0.0
    assert by_name["active"].default is True
    assert by_name["manager"].default is None
    # default_factory list, not a shared mutable default
    assert by_name["skills"].default_factory is list
    assert by_name["skills"].default is MISSING or by_name["skills"].default is None


def test_employee_constraints_and_flags_match_the_source_example():
    by_name = {f.name: f for f in dc_fields(Employee)}

    age = by_name["age"]
    assert age.metadata.get("min") == 18
    assert age.metadata.get("max") == 99

    # NOTE: the metadata key is "primary", not "primary_key" (fields.pyx
    # normalises the constructor argument); asserting the wrong key would
    # pass vacuously via .get() returning None.
    assert by_name["employee_id"].metadata.get("primary") is True
    for required in ("employee_id", "name", "age", "salary", "hired_at"):
        assert by_name[required].metadata.get("required") is True, required
    for optional in ("email", "updated_at", "manager"):
        assert by_name[optional].metadata.get("required") is False, optional


def test_employee_builds_from_both_supplied_input_forms():
    """AC: 'fixtures include both supplied input forms'."""
    native = Employee(**build_kwargs(CASES_BY_NAME["employee_native"]))
    if not HAS_RUST:
        pytest.skip(RUST_SKIP_REASON)
    raw = Employee(**build_kwargs(CASES_BY_NAME["employee_raw"]))

    for built in (raw, native):
        assert isinstance(built.employee_id, uuid.UUID)
        assert isinstance(built.age, int) and not isinstance(built.age, bool)
        assert isinstance(built.salary, Decimal)
        assert isinstance(built.hired_at, date)
        assert isinstance(built.updated_at, datetime)

    assert raw.employee_id == native.employee_id
    assert raw.age == native.age == 42
    assert raw.salary == native.salary
    assert raw.hired_at == native.hired_at
    assert raw.skills == native.skills


# ---------------------------------------------------------------------------
# Isolation: fresh mutables, preserved intra-case aliases, no shared state
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_case_payloads_are_independent_between_calls(case):
    """No mutable object may be shared between two builds of the same case."""
    first = case.build()
    second = case.build()

    assert first == second, "builders must be deterministic"
    assert first is not second

    def _walk(node):
        yield node
        if isinstance(node, dict):
            for value in node.values():
                yield from _walk(value)
        elif isinstance(node, (list, set)):
            for value in node:
                yield from _walk(value)

    mutable_ids = {
        id(node) for node in _walk(first)
        if isinstance(node, (dict, list, set, bytearray))
    }
    for node in _walk(second):
        if isinstance(node, (dict, list, set, bytearray)):
            assert id(node) not in mutable_ids, (
                f"{case.name} reuses a mutable object across builds"
            )


@pytest.mark.parametrize(
    "case", [c for c in CASES if c.aliased_args], ids=lambda c: c.name
)
def test_intra_case_aliases_are_preserved(case):
    """Deliberate aliases *inside* one payload survive rebuilding."""
    payload = case.build()
    for left, right in case.aliased_args:
        assert resolve_path(payload, left) is resolve_path(payload, right), (
            f"{case.name}: {left} and {right} must be the same object"
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_mutating_a_built_payload_cannot_leak_into_the_next_build(case):
    """The core anti-leak guarantee for reference vs. candidate runs."""
    payload = case.build()
    for key, value in list(payload.items()):
        if isinstance(value, list):
            value.append("MUTATED")
        elif isinstance(value, dict):
            value["MUTATED"] = True
        elif isinstance(value, set):
            value.add("MUTATED")

    fresh = case.build()
    for key, value in fresh.items():
        if isinstance(value, list):
            assert "MUTATED" not in value, key
        elif isinstance(value, dict):
            assert "MUTATED" not in value, key
        elif isinstance(value, set):
            assert "MUTATED" not in value, key


def test_callback_log_is_resettable_and_scoped():
    """Callback-observing cases must never inherit another case's events."""
    models_mod.reset_hook_events()
    assert models_mod.hook_events == []

    model = CASES_BY_NAME["callback_valid"].resolve_model()
    model(**build_kwargs(CASES_BY_NAME["callback_valid"]))
    first = list(models_mod.hook_events)
    assert first, "the callback case must actually invoke its callbacks"

    models_mod.reset_hook_events()
    assert models_mod.hook_events == []

    model(**build_kwargs(CASES_BY_NAME["callback_valid"]))
    assert list(models_mod.hook_events) == first, (
        "callback sequence must be reproducible once the log is reset"
    )
    models_mod.reset_hook_events()


def test_case_names_are_unique_and_models_are_registered():
    names = [case.name for case in CASES]
    assert len(names) == len(set(names))

    registered = {model.__name__ for model in ALL_MODELS}
    for case in CASES:
        assert case.model_name in registered, case.name
        assert case.resolve_model().__name__ == case.model_name


def test_every_model_class_is_distinct_and_provenanced():
    """A class-cache collision would hand two cases the same class object."""
    seen = {}
    for model in ALL_MODELS:
        assert model.__name__ not in seen, (
            f"duplicate model name {model.__name__}: metaclass cache collision"
        )
        seen[model.__name__] = model
        assert model.__name__ in PROVENANCE, model.__name__

    assert set(PROVENANCE) == set(seen)


def test_wide_model_has_fifty_fields():
    assert len(models_mod.WIDE_FIELD_NAMES) == 50
    assert len(dc_fields(models_mod.WideModel)) == 50


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_no_case_uses_a_nondeterministic_factory():
    """Two builds separated in time must be byte-identical."""
    for case in CASES:
        assert case.build() == case.build(), case.name


def test_frozen_defaults_are_used_instead_of_clocks():
    presence = models_mod.PresenceRules(
        **build_kwargs(CASES_BY_NAME["presence_minimal"])
    )
    assert presence.with_db_default == models_mod.FROZEN_NOW

    boundaries = models_mod.Boundaries(
        **build_kwargs(CASES_BY_NAME["boundaries_defaults"])
    )
    assert boundaries.a_datetime == models_mod.FROZEN_NOW


# ---------------------------------------------------------------------------
# Expectations declared by the corpus actually hold on this build
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", [c for c in CASES if c.expect == EXPECT_OK], ids=lambda c: c.name
)
def test_ok_cases_build(case):
    if case.requires_rust_parsers and not HAS_RUST:
        pytest.skip(RUST_SKIP_REASON)
    models_mod.reset_hook_events()
    try:
        instance = case.resolve_model()(**build_kwargs(case))
    finally:
        models_mod.reset_hook_events()
    assert instance is not None


@pytest.mark.parametrize(
    "case", [c for c in CASES if c.expect == EXPECT_ERROR], ids=lambda c: c.name
)
def test_error_cases_raise(case):
    if case.requires_rust_parsers and not HAS_RUST:
        pytest.skip(RUST_SKIP_REASON)
    models_mod.reset_hook_events()
    try:
        with pytest.raises(Exception) as excinfo:
            case.resolve_model()(**build_kwargs(case))
    finally:
        models_mod.reset_hook_events()
    # The differential runner pins the exact type/message/payload; here we only
    # require that the corpus' own EXPECT_ERROR label is honest.
    assert excinfo.value is not None


# ---------------------------------------------------------------------------
# examples/ coverage manifest
# ---------------------------------------------------------------------------


def test_manifest_covers_every_example_module(manifest):
    """AC: 'identifies every inventoried schema example'."""
    inventory = inventory_examples()
    recorded = manifest["examples"]

    missing = sorted(set(inventory) - set(recorded))
    extra = sorted(set(recorded) - set(inventory))
    assert not missing, f"examples missing from the manifest: {missing}"
    assert not extra, f"manifest lists modules that no longer exist: {extra}"


def test_manifest_matches_the_live_inventory(manifest):
    inventory = inventory_examples()
    for rel, observed in inventory.items():
        recorded = manifest["examples"][rel]
        assert recorded["schema_bearing"] == observed["schema_bearing"], rel
        assert recorded["models"] == observed["models"], rel
        assert recorded["executes_at_import"] == observed["executes_at_import"], rel


def test_every_schema_example_states_a_disposition_and_reason(manifest):
    """AC: 'any reason for safe adaptation instead of top-level execution'."""
    for rel, recorded in manifest["examples"].items():
        if not recorded["schema_bearing"]:
            continue
        assert recorded["disposition"] in {"adapted", "excluded"}, rel
        assert recorded["reason"].strip(), rel


def test_adapted_examples_name_real_fixture_models(manifest):
    for rel, recorded in manifest["examples"].items():
        for fixture_model in recorded.get("adapted_as", []):
            assert fixture_model in PROVENANCE, (
                f"{rel} claims to be adapted as {fixture_model}, "
                "which is not a corpus model"
            )


def test_manifest_records_why_examples_are_not_imported(manifest):
    assert manifest["policy"].strip()
    executing = [
        rel for rel, rec in manifest["examples"].items()
        if rec["schema_bearing"] and rec["executes_at_import"]
    ]
    # The whole reason the corpus re-declares schemas: most schema-bearing
    # examples run code at import time.  If that ever stops being true the
    # manifest's policy paragraph should be revisited, not silently kept.
    assert executing, (
        "no schema example executes at import any more; revisit the manifest "
        "policy instead of leaving a stale justification in place"
    )


def test_corpus_covers_the_required_behaviour_families():
    """Spec §4 'Test Data / Fixtures' enumerates what must be present."""
    required_tags = {
        "employee", "raw", "native", "scalar", "unconstrained", "constraint",
        "wide", "orm", "nested", "container", "alias", "presence", "null",
        "falsy", "db_default", "callback", "descriptor", "hook", "boundary",
        "subclass", "invalid", "identity", "order", "defaults",
        "characterization", "ignored-constraint",
    }
    present = set()
    for case in CASES:
        present.update(case.tags)
    assert required_tags <= present, sorted(required_tags - present)


def test_benchmark_cases_are_all_success_cases():
    """A timing workload must never be measuring an exception path by accident."""
    for case in CASES:
        if case.benchmark:
            assert case.expect == EXPECT_OK, case.name
            assert not case.observes_callbacks, case.name


def test_probe_keys_never_reach_the_constructor():
    for case in CASES:
        kwargs = build_kwargs(case)
        for probe in cases_mod.PROBE_KEYS:
            assert probe not in kwargs, case.name


# ---------------------------------------------------------------------------
# Callback routing (spec §2 rule 7) and the rs_parsers-absent gap (spec §4)
# ---------------------------------------------------------------------------


def test_callback_routes_match_the_reference():
    """Exactly the two live callbacks fire; the two dead ones stay dead.

    ``abstract.py:257`` caches ``validators[int]`` into ``f.validator``, so
    ``converters.pyx:2354`` never reaches ``_validation``'s metadata callback
    for an ``int``; ``parse_basic`` (``converters.pyx:964``) returns before its
    encoder branch for a ``str``.  Both dead routes are pinned here because a
    "unified callback" refactor would start invoking them -- a behaviour
    change, not an optimisation.
    """
    case = CASES_BY_NAME["callback_valid"]
    models_mod.reset_hook_events()
    try:
        instance = case.resolve_model()(**build_kwargs(case))
        fired = [name for name, _ in models_mod.hook_events]
    finally:
        models_mod.reset_hook_events()

    assert fired == ["no_empty_tag", "scaling_encoder"], fired
    assert "never_called_validator" not in fired
    assert "never_called_encoder" not in fired

    # The live encoder really did transform the value...
    assert instance.live_scaled == 5.0
    # ...and the dead one really did not.
    assert instance.dead_encoder == "quiet"
    # The dead validator returns False for every input yet nothing was rejected.
    assert instance.dead_validator == 3


def test_container_validator_rejection_is_observed():
    case = CASES_BY_NAME["callback_rejected"]
    models_mod.reset_hook_events()
    try:
        with pytest.raises(Exception):
            case.resolve_model()(**build_kwargs(case))
        fired = [name for name, _ in models_mod.hook_events]
    finally:
        models_mod.reset_hook_events()

    assert "no_empty_tag" in fired


def test_rs_parsers_absent_gap_is_characterized():
    """Spec §4: characterise the rs_parsers-absent behaviour, do not paper over it.

    ``converters.pyx:199,236`` call ``rc.to_date``/``rc.to_datetime``
    unconditionally, but ``datamodel/rs_parsers/__init__.py`` only defines
    ``HAS_RUST = False`` when the extension is missing.  The reference commit
    ``d932c720`` has the identical call sites, so this is a *shared* gap and
    not a regression introduced by this feature -- but it must be visible.
    """
    case = CASES_BY_NAME["unconstrained_raw"]
    assert case.requires_rust_parsers is True

    if HAS_RUST:
        instance = case.resolve_model()(**build_kwargs(case))
        assert isinstance(instance.a_date, date)
        assert isinstance(instance.a_datetime, datetime)
        return

    with pytest.raises(Exception) as excinfo:
        case.resolve_model()(**build_kwargs(case))
    payload = getattr(excinfo.value, "payload", None) or {}
    assert "a_date" in payload or "a_date" in str(excinfo.value), (
        "the rust-absent failure should still be attributed to the date field"
    )


def test_every_characterization_case_explains_itself():
    """A 'characterization' case pins a quirk, so it must say which quirk."""
    for case in CASES:
        if "characterization" in case.tags:
            assert case.notes.strip(), case.name
            assert "VERIFIED" in case.notes or "verified" in case.notes, case.name
