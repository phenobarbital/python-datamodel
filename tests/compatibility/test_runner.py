"""Tests for the FEAT-2 differential runner (TASK-8).

Two questions are answered here, and they are different questions:

1. **Is the harness itself trustworthy?**  A comparator that never reports a
   difference would make every future task pass vacuously, so the bulk of this
   module *seeds* divergences — int vs. bool, same value/different type, error
   order, shared-default contamination, changed callback counts — and requires
   each to be detected with an actionable path.  These tests need no reference
   build and always run.

2. **Do the reference and the candidate actually agree?**  That needs the
   rebuilt engineering reference.  Those tests skip, loudly and with the reason
   recorded, when it is absent — a missing reference is never a pass.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tests.compatibility.observations import (
    FORMAT_VERSION,
    Divergence,
    Observer,
    compare,
)
from tests.compatibility.runner import (
    DEFAULT_MANIFEST_PATH,
    REFERENCE_COMMIT,
    REFERENCE_VERSION,
    Environment,
    ProvenanceError,
    RunResult,
    RunnerError,
    candidate_environment,
    compare_runs,
    describe_divergences,
    describe_environment,
    load_manifest,
    reference_environment,
    run_environment,
    verify_manifest,
)

REFERENCE_MISSING = (
    "the rebuilt engineering reference "
    f"({REFERENCE_COMMIT[:8]}, {REFERENCE_VERSION}) is not present. "
    "Create a detached worktree at ../ref-FEAT-2-d932c720 with its own .venv "
    "and `uv pip install -e '.[dev]'`, or set $DATAMODEL_REFERENCE_ROOT. "
    "A skipped comparison is NOT a passing comparison."
)


@pytest.fixture(scope="module")
def reference_env():
    env = reference_environment()
    if env is None or not env.python.is_file():
        pytest.skip(REFERENCE_MISSING)
    return env


@pytest.fixture(scope="module")
def candidate_env():
    env = candidate_environment()
    if not env.python.is_file():
        pytest.skip(
            "the candidate worktree has no .venv; create one before running "
            "the differential harness"
        )
    return env


@pytest.fixture(scope="module")
def reference_run(reference_env):
    return run_environment(reference_env)


@pytest.fixture(scope="module")
def candidate_run(candidate_env):
    return run_environment(candidate_env)


# ===========================================================================
# Part 1 -- the comparator detects what it must (no reference build needed)
# ===========================================================================


def _observed(value):
    return Observer().observe(value)


def test_identical_values_compare_equal():
    for value in (
        42, "hello", 4.75, True, Decimal("85000.50"), b"bytes",
        date(2020, 3, 15), datetime(2026, 9, 8, 10, 30),
        uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        ["a", "b"], {"k": [1, 2]}, (1.0, 2.0), None,
    ):
        assert compare(_observed(value), _observed(value)) == [], value


def test_int_versus_bool_is_detected():
    """``True == 1`` in Python; the corpus must never let that pass."""
    divergences = compare(_observed(1), _observed(True))
    assert divergences, "1 and True must not compare equal"
    assert divergences[0].kind == "kind"
    assert divergences[0].reference == "int"
    assert divergences[0].candidate == "bool"


def test_same_value_different_type_is_detected():
    """Decimal/str, date/datetime, int/float, str/bytes must all diverge."""
    pairs = [
        (Decimal("1.0"), "1.0"),
        (date(2020, 3, 15), datetime(2020, 3, 15)),
        (1, 1.0),
        ("abc", b"abc"),
        ([1, 2], (1, 2)),
        (uuid.UUID(int=0), str(uuid.UUID(int=0))),
    ]
    for left, right in pairs:
        divergences = compare(_observed(left), _observed(right))
        assert divergences, f"{left!r} and {right!r} must not compare equal"
        assert divergences[0].kind in {"kind", "class"}, (left, right, divergences)


def test_str_subclass_is_distinguished_from_str():
    class Shouty(str):
        pass

    divergences = compare(_observed("abc"), _observed(Shouty("abc")))
    assert divergences
    assert divergences[0].kind == "class"
    assert "Shouty" in str(divergences[0].candidate)


def test_arbitrary_precision_integers_survive_the_process_boundary():
    """A 2**96 integer must not be rounded into a float by the transport."""
    big = 2 ** 96 + 1
    observation = _observed(big)
    # Round-trip through JSON exactly as the child does.
    restored = json.loads(json.dumps(observation))
    assert restored["v"] == str(big)
    assert compare(observation, _observed(big + 1))


def test_dict_ordering_is_detected():
    """Error payload order is observable through ValidationError's message."""
    divergences = compare(
        _observed({"a": 1, "b": 2}), _observed({"b": 2, "a": 1})
    )
    assert divergences, "a reordered mapping must be reported"


def test_shared_default_contamination_is_detected():
    """Two fields aliasing one list vs. two independent lists."""
    shared = []
    contaminated = {"left": shared, "right": shared}
    independent = {"left": [], "right": []}

    divergences = compare(_observed(contaminated), _observed(independent))
    assert divergences, "aliased and independent containers must not compare equal"
    # The aliased run reports a second sighting; the independent one a fresh list.
    kinds = {d.kind for d in divergences}
    assert "kind" in kinds or "class" in kinds


def test_alias_relationships_are_compared_not_addresses():
    """The *same* aliasing pattern compares equal across two separate builds."""
    def build():
        shared = ["x"]
        return {"left": shared, "right": shared}

    # Two distinct object graphs, identical relationships.
    assert compare(_observed(build()), _observed(build())) == []


def test_cycles_do_not_hang_the_observer():
    node = {}
    node["self"] = node
    observation = _observed(node)
    assert observation["k"] == "dict"
    assert compare(observation, _observed({"self": {}})), "a cycle must be visible"


def test_divergence_paths_are_actionable():
    reference = _observed({"employee": {"age": 42, "skills": ["python"]}})
    candidate = _observed({"employee": {"age": 43, "skills": ["python"]}})
    divergences = compare(reference, candidate, "$.cases.employee_native")
    assert divergences
    joined = " ".join(d.path for d in divergences)
    assert "$.cases.employee_native" in joined
    assert "42" in describe_divergences(divergences)


def test_describe_divergences_reports_a_count_and_truncates():
    many = [Divergence(f"$[{i}]", "value", i, i + 1) for i in range(25)]
    text = describe_divergences(many, limit=5)
    assert text.startswith("25 divergence(s):")
    assert "and 20 more" in text
    assert describe_divergences([]) == "no divergences"


# -- seeded divergences on whole run records --------------------------------


def _fake_run(name: str, cases: dict) -> RunResult:
    return RunResult(name, {"version": "x"}, cases)


def _minimal_case(**overrides) -> dict:
    base = {
        "format_version": FORMAT_VERSION,
        "case": "demo",
        "model": "Employee",
        "declared_expectation": "ok",
        "outcome": "ok",
        "error": None,
        "instance": _observed({"age": 42}),
        "input_before": _observed({"age": 42}),
        "input_after": _observed({"age": 42}),
        "callbacks": [],
        "callback_counts": {},
        "fresh_results": {"supported": True, "error": None,
                          "same_object": False, "equal": True, "keys": ["age"]},
    }
    base.update(overrides)
    return base


def test_identical_runs_compare_equal():
    left = _fake_run("reference", {"demo": _minimal_case()})
    right = _fake_run("candidate", {"demo": _minimal_case()})
    assert compare_runs(left, right) == []


def test_changed_callback_count_is_detected():
    left = _fake_run("reference", {"demo": _minimal_case(
        callbacks=[["validate", _observed(1)]], callback_counts={"validate": 1},
    )})
    right = _fake_run("candidate", {"demo": _minimal_case(
        callbacks=[["validate", _observed(1)], ["validate", _observed(1)]],
        callback_counts={"validate": 2},
    )})
    divergences = compare_runs(left, right)
    paths = [d.path for d in divergences]
    assert any("callback_counts" in path for path in paths), divergences


def test_error_payload_order_is_detected():
    left = _fake_run("reference", {"demo": _minimal_case(
        outcome="error", instance=None, fresh_results=None,
        error={"type": "ValidationError", "module": "datamodel.exceptions",
               "message": "boom", "args": [], "payload": _observed({"a": 1, "b": 2}),
               "payload_order": ["a", "b"], "cause": None, "context": None},
    )})
    right = _fake_run("candidate", {"demo": _minimal_case(
        outcome="error", instance=None, fresh_results=None,
        error={"type": "ValidationError", "module": "datamodel.exceptions",
               "message": "boom", "args": [], "payload": _observed({"b": 2, "a": 1}),
               "payload_order": ["b", "a"], "cause": None, "context": None},
    )})
    divergences = compare_runs(left, right)
    paths = [d.path for d in divergences]
    assert any("payload_order" in path for path in paths), divergences


def test_outcome_flip_is_detected():
    left = _fake_run("reference", {"demo": _minimal_case()})
    right = _fake_run("candidate", {"demo": _minimal_case(
        outcome="error", instance=None, fresh_results=None,
        error={"type": "ValidationError", "module": "datamodel.exceptions",
               "message": "boom", "args": [], "payload": None,
               "cause": None, "context": None},
    )})
    divergences = compare_runs(left, right)
    assert any(d.path.endswith(".outcome") for d in divergences), divergences


def test_input_mutation_difference_is_detected():
    left = _fake_run("reference", {"demo": _minimal_case()})
    right = _fake_run("candidate", {"demo": _minimal_case(
        input_after=_observed({"age": 42, "injected": True}),
    )})
    divergences = compare_runs(left, right)
    assert any("input_after" in d.path for d in divergences), divergences


def test_shared_success_result_is_detected():
    """A ``to_dict`` that stops returning a fresh mapping must be caught."""
    left = _fake_run("reference", {"demo": _minimal_case()})
    right = _fake_run("candidate", {"demo": _minimal_case(
        fresh_results={"supported": True, "error": None, "same_object": True,
                       "equal": True, "keys": ["age"]},
    )})
    divergences = compare_runs(left, right)
    assert any("same_object" in d.path for d in divergences), divergences


def test_missing_case_is_detected():
    left = _fake_run("reference", {"demo": _minimal_case(), "other": _minimal_case()})
    right = _fake_run("candidate", {"demo": _minimal_case()})
    divergences = compare_runs(left, right)
    assert any(d.kind == "missing-in-candidate" for d in divergences), divergences


# ===========================================================================
# Part 2 -- provenance and isolation
# ===========================================================================


def test_environment_rejects_a_root_without_datamodel(tmp_path):
    env = Environment("bogus", tmp_path, tmp_path / "python")
    with pytest.raises(ProvenanceError, match="does not contain a datamodel package"):
        env.validate()


def test_environment_rejects_a_missing_interpreter(tmp_path):
    (tmp_path / "datamodel").mkdir()
    (tmp_path / "datamodel" / "__init__.py").write_text("")
    env = Environment("bogus", tmp_path, tmp_path / "nope" / "python")
    with pytest.raises(ProvenanceError, match="interpreter does not exist"):
        env.validate()


def test_environment_does_not_resolve_the_venv_symlink(candidate_env):
    """Resolving ``.venv/bin/python`` would launch the *base* interpreter.

    That silently drops site-packages, so ``datamodel``'s dependencies vanish
    and every child fails with an unrelated ImportError.
    """
    assert ".venv" in candidate_env.python.parts


def test_two_environments_sharing_one_artifact_are_rejected(candidate_env, tmp_path):
    """The core isolation guard, in its realistic shape.

    The mistake this task exists to prevent is a second "environment" that is
    really a view onto the first one's compiled artifacts — a symlinked or
    copied package directory.  Here the decoy root's ``datamodel`` is a symlink
    to the candidate's, so the child resolves the import back to the candidate
    tree and must refuse to describe it as an independent environment.
    """
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    try:
        (decoy / "datamodel").symlink_to(
            candidate_env.root / "datamodel", target_is_directory=True
        )
    except (OSError, NotImplementedError):  # pragma: no cover - platform guard
        pytest.skip("this platform does not allow creating directory symlinks")

    env = Environment("decoy", decoy, candidate_env.python)
    with pytest.raises(ProvenanceError, match="not isolated"):
        describe_environment(env)


def test_a_mixed_environment_is_rejected(candidate_env, tmp_path):
    """A root whose *submodules* come from elsewhere must be rejected.

    An editable install registers a meta-path finder keyed on the full dotted
    name, so a decoy root containing only an empty ``datamodel/__init__.py``
    still gets ``datamodel.converters`` from the real tree.  Half of one build
    and half of another would make every timing and every comparison
    meaningless, so it is a hard error rather than a filtered-out oddity.
    """
    decoy = tmp_path / "empty"
    (decoy / "datamodel").mkdir(parents=True)
    (decoy / "datamodel" / "__init__.py").write_text("")
    env = Environment("decoy", decoy, candidate_env.python)
    with pytest.raises(ProvenanceError) as excinfo:
        describe_environment(env)
    assert "not isolated" in str(excinfo.value)
    assert "datamodel.converters" in str(excinfo.value)


def test_provenance_guard_rejects_a_foreign_root(tmp_path):
    """Unit-test the in-child guard directly, without a subprocess."""
    from tests.compatibility.runner import _ChildProvenanceError, _child_provenance

    with pytest.raises(_ChildProvenanceError, match="not isolated"):
        _child_provenance(tmp_path.resolve())


def test_manifest_is_present_and_names_the_specified_reference():
    manifest = load_manifest()
    assert manifest["reference_commit"] == REFERENCE_COMMIT
    assert manifest["reference_version"] == REFERENCE_VERSION
    assert set(manifest["environments"]) == {"reference", "candidate"}


def test_manifest_records_separately_built_environments():
    """Two environments must load from two *directories*.

    Byte-equal artifacts are deliberately not treated as a fault: with the
    Rust and Cython sources currently identical between 0.10.21 and the
    candidate, a reproducible build legitimately yields the same bytes at two
    different paths.  What must never happen is both environments importing the
    *same file*.
    """
    manifest = load_manifest()
    reference = manifest["environments"]["reference"]
    candidate = manifest["environments"]["candidate"]

    assert reference["binaries"] and candidate["binaries"]
    assert set(reference["binaries"]) == set(candidate["binaries"]), (
        "the same set of extension modules should be built in both environments"
    )
    assert reference["datamodel_file"] != candidate["datamodel_file"]
    assert reference["package_dir"] != candidate["package_dir"]
    assert reference["root"] != candidate["root"]


def test_manifest_records_matching_backend_availability():
    """A backend present on one side only would fake divergences (or hide them).

    Verified experimentally while building this harness: with ``rs_parsers``
    present on the candidate and absent on the reference, ``employee_raw`` and
    ``unconstrained_raw`` diverge (outcome ``error`` -> ``ok``) purely because
    ``converters.pyx:199,236`` dereference ``rc.to_date``/``rc.to_datetime``
    unconditionally.  That is a *setup* artefact, not a code change.
    """
    manifest = load_manifest()
    reference = manifest["environments"]["reference"]
    candidate = manifest["environments"]["candidate"]
    assert reference["has_rust_parsers"] == candidate["has_rust_parsers"]


def test_manifest_records_the_reference_version():
    manifest = load_manifest()
    assert manifest["environments"]["reference"]["version"] == REFERENCE_VERSION
    assert manifest["environments"]["reference"]["git"]["commit"] == REFERENCE_COMMIT


def test_verify_manifest_detects_a_stale_binary(reference_env, candidate_env):
    manifest = load_manifest()
    tampered = json.loads(json.dumps(manifest))
    binaries = tampered["environments"]["candidate"]["binaries"]
    first = sorted(binaries)[0]
    binaries[first] = "0" * 64

    problems = verify_manifest(tampered, [candidate_env])
    assert any("stale" in problem for problem in problems), problems
    assert any(first in problem for problem in problems), problems


def test_verify_manifest_detects_a_wrong_reference_commit(candidate_env):
    manifest = load_manifest()
    tampered = json.loads(json.dumps(manifest))
    tampered["reference_commit"] = "0" * 40
    problems = verify_manifest(tampered, [])
    assert any("reference_commit" in problem for problem in problems), problems


def test_verify_manifest_detects_a_missing_environment(candidate_env):
    tampered = {"reference_commit": REFERENCE_COMMIT, "environments": {}}
    problems = verify_manifest(tampered, [candidate_env])
    assert any("absent from the manifest" in problem for problem in problems), problems


def test_live_manifest_still_matches_the_built_artifacts(
    reference_env, candidate_env
):
    """If this fails, the artifacts were rebuilt: regenerate the manifest.

    ``python tests/compatibility/runner.py --write-manifest``
    """
    problems = verify_manifest(load_manifest(), [reference_env, candidate_env])
    assert problems == [], "\n".join(problems)


# ===========================================================================
# Part 3 -- the real reference/candidate differential
# ===========================================================================


def test_reference_and_candidate_load_different_builds(reference_run, candidate_run):
    assert reference_run.provenance["version"] == REFERENCE_VERSION
    assert reference_run.provenance["git"]["commit"] == REFERENCE_COMMIT
    assert (
        reference_run.provenance["datamodel_file"]
        != candidate_run.provenance["datamodel_file"]
    )
    assert (
        reference_run.provenance["has_rust_parsers"]
        == candidate_run.provenance["has_rust_parsers"]
    ), (
        "reference and candidate must have matching backend availability; "
        "otherwise every date/datetime divergence is an artefact of the setup"
    )


def test_a_reference_run_compares_equal_to_itself(reference_env):
    """Two fresh reference processes must be indistinguishable."""
    first = run_environment(reference_env)
    second = run_environment(reference_env)
    divergences = compare_runs(first, second)
    assert divergences == [], describe_divergences(divergences)


def test_reference_and_candidate_agree_on_every_case(reference_run, candidate_run):
    """The differential itself: AC2/AC4/AC7 evidence for every corpus case."""
    assert set(reference_run.cases) == set(candidate_run.cases)
    assert len(reference_run.cases) >= 40
    divergences = compare_runs(reference_run, candidate_run)
    assert divergences == [], describe_divergences(divergences, limit=40)


def test_every_case_ran_exactly_once(reference_run):
    """No live callback may execute twice: one build per case, per run."""
    from tests.fixtures.model_performance.cases import CASES_BY_NAME

    for name, record in reference_run.cases.items():
        case = CASES_BY_NAME[name]
        if not case.observes_callbacks:
            continue
        counts = record["callback_counts"]
        assert counts, f"{name} declares observes_callbacks but logged none"
        for callback, count in counts.items():
            assert count == 1, (
                f"{name}: {callback} ran {count} times in a single build"
            )


def test_declared_expectations_match_the_reference(reference_run):
    """The corpus' EXPECT_OK/EXPECT_ERROR labels are honest on the oracle."""
    from tests.fixtures.model_performance.cases import CASES_BY_NAME

    has_rust = reference_run.provenance["has_rust_parsers"]
    for name, record in reference_run.cases.items():
        case = CASES_BY_NAME[name]
        if case.requires_rust_parsers and not has_rust:
            continue  # characterized separately; see test_fixture_corpus.py
        assert record["outcome"] == case.expect, (
            f"{name}: reference outcome {record['outcome']!r} but the corpus "
            f"declares {case.expect!r}"
        )


def test_error_cases_carry_a_comparable_payload(reference_run, candidate_run):
    """Error contents, not just error presence, are part of the contract."""
    compared = 0
    for name, record in reference_run.cases.items():
        if record["outcome"] != "error":
            continue
        candidate = candidate_run.cases[name]
        assert candidate["outcome"] == "error", name
        assert record["error"]["type"] == candidate["error"]["type"], name
        assert record["error"]["message"] == candidate["error"]["message"], name
        assert record["error"].get("payload_order") == candidate["error"].get(
            "payload_order"
        ), name
        compared += 1
    assert compared >= 8, f"only {compared} error cases were compared"


def test_success_results_stay_independently_mutable(reference_run, candidate_run):
    """AC7: externally returned dictionaries must remain fresh per call."""
    checked = 0
    for name, record in reference_run.cases.items():
        fresh = record["fresh_results"]
        if not fresh or not fresh.get("supported") or fresh.get("error"):
            continue
        assert fresh["same_object"] is False, (
            f"{name}: to_dict() returned the same object twice on the reference"
        )
        assert candidate_run.cases[name]["fresh_results"] == fresh, name
        checked += 1
    assert checked >= 20, f"only {checked} success results were checked"


def test_runner_reports_an_unknown_case_name(candidate_env):
    with pytest.raises(RunnerError, match="unknown case"):
        run_environment(candidate_env, cases=["definitely-not-a-case"])


def test_runner_can_select_a_subset(candidate_env):
    result = run_environment(candidate_env, cases=["employee_native", "org_strict"])
    assert set(result.cases) == {"employee_native", "org_strict"}


def test_manifest_path_is_inside_the_harness():
    assert DEFAULT_MANIFEST_PATH.name == "reference_manifest.json"
    assert DEFAULT_MANIFEST_PATH.parent.name == "compatibility"
    assert Path(DEFAULT_MANIFEST_PATH).is_file()
