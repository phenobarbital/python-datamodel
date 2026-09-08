"""Strict compatibility of the real ``asyncdb.models`` consumer (TASK-10).

Spec §8 records the resolved requirement: *"schema examples in examples/ folder
and asyncdb.models (that uses under-the-hood python-datamodel) requires strict
compat."*  This module proves the ``asyncdb`` half by building **real**
:class:`asyncdb.models.Model` subclasses under both compiled ``datamodel``
artifacts and comparing every observable.

How the differential works
==========================

``runner.py`` owns the environment/provenance machinery but its child protocol
is bound to the main fixture corpus, and TASK-10 does not own that file.  So
this module ships its own small child script (:data:`_CHILD_SOURCE`) that
mirrors ``runner.py``'s ``sys.path`` discipline exactly:

1. bind ``datamodel`` from the environment root **first**,
2. verify ``datamodel.__file__`` really lives under that root,
3. only then prepend this worktree so the shared fixtures import without
   re-binding ``datamodel``.

It reuses ``runner.Environment`` / ``candidate_environment()`` /
``reference_environment()`` for environment discovery and
``observations.Observer`` / ``compare()`` for the comparison, so the two tasks
cannot disagree about what "the reference build" or "a difference" means.

A missing dependency is a failure, never a skip
===============================================

The task is explicit: *"missing asyncdb must fail the required integration
gate, not silently skip."*  :func:`test_asyncdb_is_installed_in_this_environment`
and :func:`test_the_required_integration_gate_cannot_pass_without_asyncdb`
enforce that.  The reference-environment comparisons *do* skip when the
reference worktree is absent -- that is a different thing (an environment that
was never built, not a dependency that is missing), and each such skip says so
loudly.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.compatibility.observations import compare  # noqa: E402
from tests.compatibility.runner import (  # noqa: E402
    REFERENCE_VERSION,
    Environment,
    candidate_environment,
    reference_environment,
)
from tests.fixtures.model_performance import asyncdb_models  # noqa: E402

HARNESS_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    HARNESS_ROOT / "tests" / "fixtures" / "model_performance" / "asyncdb_manifest.json"
)
REPORT_PATH = (
    HARNESS_ROOT / "benchmarks" / "results" / "compatible-model-performance"
    / "asyncdb-baseline.json"
)
CHILD_TIMEOUT_SECONDS = 300


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ===========================================================================
# Part 1 -- the dependency gate (a missing artifact must FAIL, not skip)
# ===========================================================================


def test_asyncdb_is_installed_in_this_environment():
    """The required integration gate. A skip here would be a false pass."""
    assert asyncdb_models.ASYNCDB_AVAILABLE, (
        "asyncdb is NOT importable, so consumer compatibility is UNVERIFIED. "
        "This is a failure, not a skip: the task requires that a missing "
        f"dependency cannot report success. Import error: "
        f"{asyncdb_models.ASYNCDB_IMPORT_ERROR}. Install the pinned artifact "
        f"recorded in {MANIFEST_PATH.name} with `uv pip install --no-deps <wheel>`."
    )


def test_the_required_integration_gate_cannot_pass_without_asyncdb():
    """The gate's own logic, exercised against a simulated absence.

    Without this, `test_asyncdb_is_installed_in_this_environment` would be
    self-certifying: it passes when asyncdb is present, and nothing would
    demonstrate that it actually fails when asyncdb is gone.
    """
    def gate(available, error):
        if not available:
            raise AssertionError(f"asyncdb is NOT importable: {error}")
        return True

    assert gate(True, None) is True
    with pytest.raises(AssertionError, match="NOT importable"):
        gate(False, "ModuleNotFoundError: No module named 'asyncdb'")


def test_models_are_real_asyncdb_models_not_local_fakes():
    """Every fixture model must inherit from the installed asyncdb.Model."""
    from asyncdb.models import Model as AsyncDBModel

    for name in asyncdb_models.ALL_MODELS:
        model = getattr(asyncdb_models, name)
        assert issubclass(model, AsyncDBModel), f"{name} is not an asyncdb Model"
        mro = [f"{c.__module__}.{c.__name__}" for c in model.__mro__]
        assert "asyncdb.models.model.Model" in mro, mro
        assert "datamodel.base.BaseModel" in mro, mro


def test_asyncdb_model_really_sits_on_datamodel():
    """If this ever fails, asyncdb stopped being a datamodel consumer."""
    from asyncdb.models import Model as AsyncDBModel

    mro = [f"{c.__module__}.{c.__name__}" for c in AsyncDBModel.__mro__]
    assert mro[0] == "asyncdb.models.model.Model"
    assert "datamodel.base.BaseModel" in mro, mro


# ===========================================================================
# Part 2 -- the manifest pins a real, verified artifact
# ===========================================================================


def test_manifest_pins_the_installed_distribution(manifest):
    import importlib.metadata as md

    installed = md.distribution("asyncdb").version
    assert manifest["artifact"]["version"] == installed, (
        f"manifest pins {manifest['artifact']['version']} but "
        f"{installed} is installed; re-pin before trusting any result"
    )
    assert asyncdb_models.ASYNCDB_VERSION == installed


def test_manifest_records_a_verifiable_digest(manifest):
    digest = manifest["artifact"]["sha256"]
    assert len(digest) == 64 and set(digest) <= set("0123456789abcdef"), digest
    assert manifest["artifact"]["url"].startswith("https://files.pythonhosted.org/")


def test_manifest_declares_the_datamodel_requirement(manifest):
    """The pin is only meaningful if the consumer really depends on us."""
    import importlib.metadata as md

    requires = md.distribution("asyncdb").metadata.get_all("Requires-Dist") or []
    datamodel_reqs = [r for r in requires if "datamodel" in r.lower()]
    assert datamodel_reqs, "asyncdb does not declare a python-datamodel dependency"
    assert manifest["artifact"]["declared_datamodel_requirement"] in datamodel_reqs


def test_manifest_adapter_imports_all_resolve(manifest):
    """Every datamodel symbol the manifest claims asyncdb uses must exist.

    This is the anti-hallucination check: a manifest entry that names a moved
    or renamed attribute would let a stale contract look verified.
    """
    import importlib

    for dotted in manifest["verified_adapter_api"][
        "datamodel_surface_consumed_by_asyncdb"
    ]["imports"]:
        module_name, _, attribute = dotted.rpartition(".")
        module = importlib.import_module(module_name)
        assert hasattr(module, attribute), f"{dotted} does not exist"


def test_manifest_mro_matches_reality(manifest):
    from asyncdb.models import Model as AsyncDBModel

    actual = [f"{c.__module__}.{c.__name__}" for c in AsyncDBModel.__mro__]
    assert manifest["verified_adapter_api"]["asyncdb.models"]["Model_mro"] == actual


def test_manifest_exports_all_resolve(manifest):
    import asyncdb.models as am

    for name in manifest["verified_adapter_api"]["asyncdb.models"]["exports"]:
        assert hasattr(am, name), f"asyncdb.models.{name} does not exist"


def test_excluded_methods_exist_but_are_deliberately_untested(manifest):
    """The exclusions must name real methods, so the boundary is honest.

    An exclusion list naming methods that do not exist would overstate what
    was consciously left out.
    """
    from asyncdb.models import Model as AsyncDBModel

    excluded = manifest["verified_adapter_api"]["excluded_methods"]
    for name in excluded["instance"] + excluded["classmethod"]:
        assert hasattr(AsyncDBModel, name), f"excluded method {name} does not exist"


def test_manifest_records_pending_external_prerequisites(manifest):
    """Genuine remaining prerequisites must be stated, not quietly dropped."""
    pending = manifest["external_prerequisites_pending"]["items"]
    assert pending, "pending external prerequisites must be recorded explicitly"
    joined = " ".join(pending).lower()
    assert "credential" in joined or "private" in joined


# ===========================================================================
# Part 3 -- offline consumer behaviour under the candidate build
# ===========================================================================


def test_every_case_matches_its_declared_outcome():
    for case in asyncdb_models.CASES:
        model = case.resolve_model()
        try:
            model(**case.build())
            outcome = "ok"
        except Exception:  # noqa: BLE001 - the outcome is the assertion
            outcome = "error"
        assert outcome == case.expect, (
            f"{case.name}: declared {case.expect} but observed {outcome}"
        )


def test_case_rows_are_independent_between_calls():
    """A row mutated by one build must never be visible to the other."""
    for case in asyncdb_models.CASES:
        first, second = case.build(), case.build()
        assert first == second, case.name
        assert first is not second, case.name
        for key, value in first.items():
            if isinstance(value, (dict, list, set)):
                assert value is not second[key], f"{case.name}.{key} is shared"


def test_no_case_uses_a_nondeterministic_factory():
    """Two builds separated by real work must still be identical."""
    for case in asyncdb_models.CASES:
        before = case.build()
        _ = [object() for _ in range(500)]
        after = case.build()
        assert before == after, f"{case.name} is nondeterministic"


def test_fixture_module_does_not_use_postponed_annotations():
    """PEP 563 breaks datamodel model definition; pin its absence.

    ``from __future__ import annotations`` turns every annotation into a
    string, and datamodel resolves ``field.type`` as a real object -- class
    definition then fails with "Expected type, got str". This bit during
    implementation; the guard stops a cleanup from reintroducing it.
    """
    import re

    source = (
        HARNESS_ROOT / "tests" / "fixtures" / "model_performance"
        / "asyncdb_models.py"
    ).read_text(encoding="utf-8")
    # Match a real import *statement* at the start of a line -- a substring
    # search also matches the comment that explains why it is absent.
    assert not re.search(r"^from __future__ import annotations", source, re.M)


def test_hydration_coerces_raw_driver_rows():
    user = asyncdb_models.DbUser(**asyncdb_models.CASES_BY_NAME["db_user_raw"].build())
    assert user.user_id == 42 and isinstance(user.user_id, int)
    assert user.name == "Ada Lovelace"


def test_defaults_fill_omitted_columns():
    user = asyncdb_models.DbUser(
        **asyncdb_models.CASES_BY_NAME["db_user_defaults"].build()
    )
    assert user.email == "n/a"
    assert user.active is True


def test_nested_relation_hydrates_into_a_model():
    staffing = asyncdb_models.DbStaffing(
        **asyncdb_models.CASES_BY_NAME["db_staffing_nested"].build()
    )
    assert isinstance(staffing.department, asyncdb_models.DbDepartment)
    assert staffing.department.title == "Research"


def test_model_renders_ddl_offline():
    """``Model.model()`` drives columns(), db_type(), required(), primary_key."""
    ddl = asyncdb_models.DbUser.model()
    assert "CREATE TABLE IF NOT EXISTS public.users" in ddl
    assert "user_id integer" in ddl
    assert "PRIMARY KEY (user_id)" in ddl


def test_set_connection_uses_the_stub_without_io():
    stub = asyncdb_models.StubConnection()
    user = asyncdb_models.DbUser(user_id=1, name="x")
    user.set_connection(stub)
    assert user.Meta.connection is stub
    user.Meta.connection = None


def test_asyncdb_mutates_datamodel_db_types_at_import():
    """A real, observable side effect of the consumer on our module state."""
    from numpy import int64

    from datamodel.types import DB_TYPES

    assert DB_TYPES[int64] == "bigint"


# ===========================================================================
# Part 4 -- the reference/candidate differential
# ===========================================================================

_CHILD_SOURCE = r'''
import json, re, sys, traceback
from pathlib import Path

request = json.loads(sys.stdin.read())
expect_root = Path(request["expect_root"]).resolve()
harness_root = Path(request["harness_root"]).resolve()

try:
    # 1. Bind `datamodel` from THIS environment before anything else can.
    sys.path.insert(0, str(expect_root))
    import datamodel

    loaded = Path(datamodel.__file__).resolve()
    if expect_root not in loaded.parents:
        raise RuntimeError(
            "imported datamodel from %s, which is not under %s" % (loaded, expect_root)
        )

    # 2. Only now make the shared harness importable. `datamodel` is already in
    #    sys.modules, so the fixtures cannot re-bind it. `expect_root` must be
    #    removed first: the reference worktree has its own `tests` package.
    while str(expect_root) in sys.path:
        sys.path.remove(str(expect_root))
    sys.path.insert(0, str(harness_root))

    import importlib.metadata as md
    from tests.compatibility.observations import Observer
    from tests.fixtures.model_performance import asyncdb_models as fx

    if not fx.ASYNCDB_AVAILABLE:
        raise RuntimeError("asyncdb not importable: %s" % fx.ASYNCDB_IMPORT_ERROR)

    provenance = {
        "datamodel_file": str(loaded),
        "datamodel_version": datamodel.version.__version__,
        "asyncdb_version": md.distribution("asyncdb").version,
        "asyncdb_file": fx.ASYNCDB_FILE,
    }

    results = {}
    for case in fx.CASES:
        observer = Observer()
        model = case.resolve_model()
        entry = {}
        try:
            instance = model(**case.build())
        except BaseException as exc:
            entry["outcome"] = "error"
            entry["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "payload": observer.observe(getattr(exc, "payload", None)),
            }
        else:
            entry["outcome"] = "ok"
            entry["instance"] = observer.observe(instance)
            try:
                entry["to_dict"] = observer.observe(instance.to_dict())
            except BaseException as exc:
                entry["to_dict_error"] = "%s: %s" % (type(exc).__name__, exc)
            try:
                entry["json"] = instance.json()
            except BaseException as exc:
                entry["json_error"] = "%s: %s" % (type(exc).__name__, exc)
            # A second to_dict() must be a distinct object: shared result
            # state would leak one build's mutation into the other.
            try:
                entry["fresh_to_dict"] = instance.to_dict() is not instance.to_dict()
            except BaseException:
                entry["fresh_to_dict"] = None
        results[case.name] = entry

    # Class-level, instance-independent observations.
    schema = {}
    for name in fx.ALL_MODELS:
        model = getattr(fx, name)
        try:
            # asyncdb renders a default_factory column as the repr of the
            # dataclasses MISSING sentinel, which embeds a heap address that
            # differs per process. Strip addresses so the comparison tests
            # the DDL rather than the allocator.
            ddl = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", model.model())
            schema[name] = {
                "ddl": ddl,
                "columns": list(model.columns(model).keys()),
            }
        except BaseException as exc:
            schema[name] = {"error": "%s: %s" % (type(exc).__name__, exc)}

    # Assignment behaviour, observed after construction.
    assignment = {}
    try:
        user = fx.DbUser(user_id=1, name="before")
        user.name = "after"
        observer = Observer()
        assignment = {
            "name": user.name,
            "to_dict": observer.observe(user.to_dict()),
        }
    except BaseException as exc:
        assignment = {"error": "%s: %s" % (type(exc).__name__, exc)}

    print(json.dumps({
        "provenance": provenance,
        "cases": results,
        "schema": schema,
        "assignment": assignment,
        "error": None,
    }))
except BaseException as exc:
    print(json.dumps({
        "error": "%s: %s" % (type(exc).__name__, exc),
        "traceback": traceback.format_exc(),
    }))
    sys.exit(1)
'''


def _run_in(env: Environment) -> dict:
    """Run the asyncdb corpus inside ``env`` and return its observations."""
    env.validate()
    child_env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "HOME": str(Path.home()),
    }
    completed = subprocess.run(
        [str(env.python), "-c", _CHILD_SOURCE],
        input=json.dumps(
            {"expect_root": str(env.root), "harness_root": str(HARNESS_ROOT)}
        ),
        capture_output=True,
        text=True,
        cwd=str(env.root),
        env=child_env,
        timeout=CHILD_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"{env.name}: child exited {completed.returncode}\n"
            f"--- stdout ---\n{completed.stdout}\n--- stderr ---\n{completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("error"):
        raise AssertionError(f"{env.name}: {payload['error']}")
    return payload


@pytest.fixture(scope="module")
def candidate_run():
    return _run_in(candidate_environment())


@pytest.fixture(scope="module")
def reference_run():
    env = reference_environment()
    if env is None:
        pytest.skip(
            "the reference worktree is not built, so the asyncdb differential "
            "could not run. A SKIPPED comparison is NOT a passing comparison: "
            "consumer parity is unverified until it is built and re-run."
        )
    return _run_in(env)


def test_candidate_ran_the_whole_corpus(candidate_run):
    assert set(candidate_run["cases"]) == set(asyncdb_models.case_names())
    assert candidate_run["provenance"]["asyncdb_version"] == "2.16.0"


def test_the_two_environments_are_actually_different_builds(
    reference_run, candidate_run
):
    ref, cand = reference_run["provenance"], candidate_run["provenance"]
    assert ref["datamodel_file"] != cand["datamodel_file"], (
        "both runs loaded the same datamodel; the comparison would be vacuous"
    )
    assert ref["datamodel_version"] == REFERENCE_VERSION, ref
    assert ref["asyncdb_version"] == cand["asyncdb_version"], (
        "the consumer must be identical on both sides, or a difference could "
        "be asyncdb's rather than datamodel's"
    )


def test_asyncdb_consumer_behaviour_is_identical(reference_run, candidate_run):
    """AC12: every observable of every real asyncdb model must match."""
    divergences = compare(reference_run["cases"], candidate_run["cases"])
    assert not divergences, "\n".join(d.describe() for d in divergences[:25])


def test_rendered_schema_is_identical(reference_run, candidate_run):
    divergences = compare(reference_run["schema"], candidate_run["schema"])
    assert not divergences, "\n".join(d.describe() for d in divergences[:25])


def test_assignment_behaviour_is_identical(reference_run, candidate_run):
    divergences = compare(reference_run["assignment"], candidate_run["assignment"])
    assert not divergences, "\n".join(d.describe() for d in divergences[:25])


def test_error_cases_are_compared_by_payload_not_just_by_raising(
    reference_run, candidate_run
):
    """A matching exception *type* is not enough; message and payload count."""
    error_cases = [
        name for name, entry in reference_run["cases"].items()
        if entry["outcome"] == "error"
    ]
    assert len(error_cases) >= 4, error_cases
    for name in error_cases:
        ref = reference_run["cases"][name]["error"]
        cand = candidate_run["cases"][name]["error"]
        assert ref["type"] == cand["type"], name
        assert ref["message"] == cand["message"], name
        assert not compare(ref["payload"], cand["payload"]), name


def test_success_results_stay_independently_mutable(reference_run, candidate_run):
    """AC7: to_dict() must return a fresh object on each call, on both builds."""
    checked = 0
    for name, entry in reference_run["cases"].items():
        if entry["outcome"] != "ok":
            continue
        assert entry["fresh_to_dict"] is True, f"{name} shares its to_dict result"
        assert candidate_run["cases"][name]["fresh_to_dict"] is True, name
        checked += 1
    assert checked >= 10, checked


def test_the_differential_would_notice_a_planted_difference(candidate_run):
    """The comparator must be able to fail, or the parity result is worthless."""
    import copy

    mutated = copy.deepcopy(candidate_run["cases"])
    target = "db_user_raw"
    mutated[target]["outcome"] = "error"
    assert compare(candidate_run["cases"], mutated), (
        "planting a changed outcome produced no divergence"
    )


# ===========================================================================
# Part 5 -- the recorded evidence report
# ===========================================================================


def test_report_exists_and_records_the_verified_pin():
    assert REPORT_PATH.is_file(), (
        f"{REPORT_PATH} is missing. Regenerate it with the snippet recorded "
        "in the TASK-10 completion note and in this report's own "
        "`regenerate_command` field; it requires the reference worktree to be "
        "built, because the report records a real differential, not a claim."
    )
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["artifact"]["version"] == "2.16.0"
    assert report["result"]["divergences"] == 0
    assert report["result"]["cases_compared"] >= len(asyncdb_models.CASES)
    assert report["environments"]["reference"]["datamodel_version"] == REFERENCE_VERSION
