"""Isolated reference/candidate compatibility runner for FEAT-2 (TASK-8).

Interface contract
==================

Dependent tasks must import *these* names and nothing else from this module::

    from tests.compatibility.runner import (
        Environment,          # frozen dataclass: name, root, python
        ProvenanceError,      # raised when two environments share an artifact
        RunResult,            # frozen dataclass: provenance, cases
        CaseObservation,      # per-case record (a plain dict wrapper)
        candidate_environment,   # () -> Environment  (this worktree)
        reference_environment,   # (root=None) -> Environment | None
        describe_environment,    # (Environment) -> dict
        run_environment,         # (Environment, cases=None) -> RunResult
        compare_runs,            # (RunResult, RunResult) -> list[Divergence]
        write_manifest,          # (list[Environment], path=None) -> dict
        load_manifest,           # (path=None) -> dict
        verify_manifest,         # (manifest, list[Environment]) -> list[str]
        DEFAULT_MANIFEST_PATH,
        REFERENCE_COMMIT, REFERENCE_VERSION,
    )

How isolation actually works
============================

Each :class:`Environment` names a *repository root* and the *interpreter of that
root's own virtualenv*.  A child process launched with that interpreter imports
``datamodel`` from that root's editable install, and only afterwards is this
worktree appended to ``sys.path`` so the shared fixture corpus
(``tests.fixtures.model_performance``) can be imported.  Because ``datamodel``
is already bound in ``sys.modules`` by then, the fixtures see the environment's
build, not this one.

The child re-checks that ``datamodel.__file__`` lives under the root it was
told to use and aborts with :class:`ProvenanceError` otherwise, so two
environments can never silently share one compiled artifact — the failure mode
this task exists to prevent.

Running this file directly is the child-process entry point; it is not a
user-facing command.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

#: The engineering reference fixed by the specification (§1).
REFERENCE_COMMIT = "d932c720e9e36bbacdaca2b1a2af0688f2636c40"
REFERENCE_VERSION = "0.10.21"

HARNESS_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent / "reference_manifest.json"

#: Where a reference worktree is expected, relative to the repository that owns
#: the git object store.  ``reference_environment()`` also honours
#: ``$DATAMODEL_REFERENCE_ROOT``.
REFERENCE_ROOT_ENV = "DATAMODEL_REFERENCE_ROOT"
DEFAULT_REFERENCE_DIRNAME = f"ref-FEAT-2-{REFERENCE_COMMIT[:8]}"

CHILD_TIMEOUT_SECONDS = 300


class ProvenanceError(RuntimeError):
    """Raised when an environment does not load the artifact it claims to."""


class RunnerError(RuntimeError):
    """Raised when a child process fails to produce a usable result."""


@dataclass(frozen=True)
class Environment:
    """A repository root plus the interpreter that must be used with it."""

    name: str
    root: Path
    python: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).resolve())
        # NOT .resolve(): a venv's bin/python is a symlink to the *base*
        # interpreter, and resolving it would launch the child outside the
        # virtualenv -- losing site-packages, and with them `datamodel`'s
        # dependencies. Normalise the path without following symlinks.
        object.__setattr__(
            self, "python", Path(os.path.abspath(os.path.expanduser(str(self.python))))
        )

    def validate(self) -> None:
        if not self.root.is_dir():
            raise ProvenanceError(f"{self.name}: root does not exist: {self.root}")
        if not (self.root / "datamodel" / "__init__.py").is_file():
            raise ProvenanceError(
                f"{self.name}: {self.root} does not contain a datamodel package"
            )
        if not self.python.is_file():
            raise ProvenanceError(
                f"{self.name}: interpreter does not exist: {self.python}\n"
                "Create the environment's own venv before running the harness."
            )


@dataclass(frozen=True)
class CaseObservation:
    """One case, observed once, in one environment."""

    name: str
    outcome: str
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def raised(self) -> bool:
        return self.outcome == "error"


@dataclass(frozen=True)
class RunResult:
    """Everything one environment reported for one invocation."""

    environment: str
    provenance: Dict[str, Any]
    cases: Dict[str, Dict[str, Any]]

    def case(self, name: str) -> CaseObservation:
        raw = self.cases[name]
        return CaseObservation(name=name, outcome=raw["outcome"], data=raw)

    def outcomes(self) -> Dict[str, str]:
        return {name: raw["outcome"] for name, raw in self.cases.items()}


# ---------------------------------------------------------------------------
# Environment discovery
# ---------------------------------------------------------------------------


def _venv_python(root: Path) -> Path:
    if os.name == "nt":  # pragma: no cover - Windows path shape
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def candidate_environment() -> Environment:
    """The environment under test: this worktree and its own venv."""
    return Environment("candidate", HARNESS_ROOT, _venv_python(HARNESS_ROOT))


def reference_environment(root: Optional[Path] = None) -> Optional[Environment]:
    """The rebuilt engineering reference, or ``None`` when it is not present.

    Returning ``None`` rather than raising lets callers *record* the absence.
    A missing reference is never a pass: :func:`compare_runs` cannot be reached
    without one, and the harness tests skip with an explicit reason.
    """
    if root is None:
        env_root = os.environ.get(REFERENCE_ROOT_ENV)
        if env_root:
            root = Path(env_root)
        else:
            root = HARNESS_ROOT.parent / DEFAULT_REFERENCE_DIRNAME
    root = Path(root)
    if not (root / "datamodel" / "__init__.py").is_file():
        return None
    return Environment("reference", root, _venv_python(root))


# ---------------------------------------------------------------------------
# Child protocol
# ---------------------------------------------------------------------------


def _invoke_child(env: Environment, request: Dict[str, Any]) -> Dict[str, Any]:
    env.validate()
    request = dict(request)
    request["harness_root"] = str(HARNESS_ROOT)
    request["expect_root"] = str(env.root)

    child_env = dict(os.environ)
    # Keep the child hermetic: no inherited PYTHONPATH, no user site packages,
    # no stray .pyc writes into either tree.
    child_env.pop("PYTHONPATH", None)
    child_env["PYTHONNOUSERSITE"] = "1"
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    child_env["PYTHONHASHSEED"] = "0"

    completed = subprocess.run(
        [str(env.python), str(Path(__file__).resolve())],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(env.root),
        env=child_env,
        timeout=CHILD_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RunnerError(
            f"{env.name}: child exited {completed.returncode}\n"
            f"--- stdout ---\n{completed.stdout}\n"
            f"--- stderr ---\n{completed.stderr}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RunnerError(
            f"{env.name}: child did not emit JSON: {exc}\n"
            f"--- stdout ---\n{completed.stdout}\n"
            f"--- stderr ---\n{completed.stderr}"
        ) from exc
    if payload.get("error"):
        detail = payload["error"]
        if detail.get("type") == "ProvenanceError":
            raise ProvenanceError(f"{env.name}: {detail['message']}")
        raise RunnerError(f"{env.name}: {detail['type']}: {detail['message']}")
    return payload


def describe_environment(env: Environment) -> Dict[str, Any]:
    """Provenance for ``env``: commit, version, artifact hashes, dependencies."""
    payload = _invoke_child(env, {"mode": "describe"})
    provenance = payload["provenance"]
    provenance["git"] = _git_provenance(env.root)
    return provenance


def run_environment(
    env: Environment, cases: Optional[Sequence[str]] = None
) -> RunResult:
    """Build every requested case exactly once in ``env`` and observe it."""
    payload = _invoke_child(
        env, {"mode": "run", "cases": list(cases) if cases is not None else None}
    )
    provenance = payload["provenance"]
    provenance["git"] = _git_provenance(env.root)
    return RunResult(env.name, provenance, payload["cases"])


def compare_runs(reference: RunResult, candidate: RunResult) -> List[Any]:
    """Every divergence between two runs, with actionable paths."""
    from tests.compatibility.observations import Divergence, compare

    divergences: List[Any] = []
    ref_names, cand_names = set(reference.cases), set(candidate.cases)
    for missing in sorted(ref_names - cand_names):
        divergences.append(
            Divergence(f"$.cases.{missing}", "missing-in-candidate", missing, None)
        )
    for added in sorted(cand_names - ref_names):
        divergences.append(
            Divergence(f"$.cases.{added}", "missing-in-reference", None, added)
        )
    for name in sorted(ref_names & cand_names):
        divergences.extend(
            compare(reference.cases[name], candidate.cases[name], f"$.cases.{name}")
        )
    return divergences


def describe_divergences(divergences: Iterable[Any], limit: int = 20) -> str:
    """A readable report for a test failure message."""
    items = list(divergences)
    if not items:
        return "no divergences"
    shown = items[:limit]
    body = "\n".join(item.describe() for item in shown)
    if len(items) > limit:
        body += f"\n... and {len(items) - limit} more"
    return f"{len(items)} divergence(s):\n{body}"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def _git_provenance(root: Path) -> Dict[str, Any]:
    """Commit and cleanliness of ``root``, resolved from the parent process."""
    def _git(*args: str) -> Optional[str]:
        try:
            out = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError):  # pragma: no cover
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    return {
        "commit": _git("rev-parse", "HEAD"),
        "describe": _git("describe", "--always", "--dirty"),
        "dirty": bool(_git("status", "--porcelain")),
    }


def write_manifest(
    environments: Sequence[Environment], path: Optional[Path] = None
) -> Dict[str, Any]:
    """Record provenance for each environment and persist it."""
    path = Path(path) if path is not None else DEFAULT_MANIFEST_PATH
    manifest: Dict[str, Any] = {
        "feature": "FEAT-2",
        "task": "TASK-8",
        "spec": "sdd/specs/compatible-model-performance.spec.md",
        "reference_commit": REFERENCE_COMMIT,
        "reference_version": REFERENCE_VERSION,
        "note": (
            "Provenance of the two isolated environments used by "
            "tests/compatibility/runner.py. `binaries` are sha256 digests of "
            "the compiled extensions actually loaded by the child process, so "
            "a stale artifact is detectable; isolation itself is checked by "
            "path, because identical sources legitimately produce "
            "byte-identical artifacts in both trees. Regenerate with "
            "`python tests/compatibility/runner.py --write-manifest` after any "
            "rebuild; verify_manifest() reports every drift. Absolute paths and "
            "digests are machine-specific by design: they record what was "
            "actually measured, and a mismatch on another machine correctly "
            "means 'rebuild and regenerate', not 'ignore'."
        ),
        "reproduce": [
            "git worktree add --detach <ref-root> " + REFERENCE_COMMIT,
            "cd <ref-root> && uv venv --python 3.13 .venv"
            " && uv pip install --python .venv/bin/python -e '.[dev]'",
            "cd <ref-root>/rust/rs_parsers && cargo build --release",
            "cp <ref-root>/rust/target/release/lib_rs_parsers.so"
            " <ref-root>/datamodel/rs_parsers/_rs_parsers.<abi>.so",
            "repeat for the candidate worktree, then"
            " python tests/compatibility/runner.py --write-manifest",
        ],
        "backend_note": (
            "Both environments are recorded WITH the rs_parsers extension "
            "built. That is not cosmetic: converters.pyx:199,236 dereference "
            "rc.to_date / rc.to_datetime unconditionally, and "
            "datamodel/rs_parsers/__init__.py defines only HAS_RUST = False "
            "when the extension is missing, so every string->date/datetime "
            "conversion fails without it. The engineering reference has the "
            "identical call sites, so the gap is shared rather than a "
            "regression -- but with rs_parsers absent the repository suite has "
            "17 pre-existing failures/errors, and with it present the suite is "
            "fully green. Reference and candidate must always be built with "
            "MATCHING backend availability, or corpus cases employee_raw and "
            "unconstrained_raw diverge for setup reasons alone."
        ),
        "environments": {},
    }
    for env in environments:
        manifest["environments"][env.name] = describe_environment(env)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return manifest


def load_manifest(path: Optional[Path] = None) -> Dict[str, Any]:
    path = Path(path) if path is not None else DEFAULT_MANIFEST_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(
    manifest: Dict[str, Any], environments: Sequence[Environment]
) -> List[str]:
    """Problems with ``manifest`` relative to the live ``environments``.

    An empty list means the recorded provenance still describes what is
    installed.  Every entry is a human-readable, actionable sentence.
    """
    problems: List[str] = []
    recorded = manifest.get("environments", {})

    if manifest.get("reference_commit") != REFERENCE_COMMIT:
        problems.append(
            f"manifest reference_commit {manifest.get('reference_commit')!r} "
            f"!= specification reference {REFERENCE_COMMIT!r}"
        )

    # Isolation is a property of *paths*, not of bytes. Two environments whose
    # Rust/Cython sources are identical will produce byte-identical artifacts
    # from a reproducible build; that is healthy, not a fault. The fault is two
    # environments loading the *same file*.
    seen_package_dirs: Dict[str, str] = {}
    for env in environments:
        entry = recorded.get(env.name)
        if entry is None:
            problems.append(f"{env.name}: absent from the manifest")
            continue
        try:
            live = describe_environment(env)
        except (ProvenanceError, RunnerError) as exc:
            problems.append(f"{env.name}: cannot be described: {exc}")
            continue

        if entry.get("datamodel_file") != live.get("datamodel_file"):
            problems.append(
                f"{env.name}: loads {live.get('datamodel_file')!r}, "
                f"manifest recorded {entry.get('datamodel_file')!r}"
            )
        if entry.get("version") != live.get("version"):
            problems.append(
                f"{env.name}: version {live.get('version')!r}, "
                f"manifest recorded {entry.get('version')!r}"
            )
        for name, digest in sorted(live.get("binaries", {}).items()):
            recorded_digest = entry.get("binaries", {}).get(name)
            if recorded_digest is None:
                problems.append(f"{env.name}: {name} is not in the manifest")
            elif recorded_digest != digest:
                problems.append(
                    f"{env.name}: {name} is stale "
                    f"(sha256 {digest[:12]}..., manifest {recorded_digest[:12]}...)"
                )

        package_dir = live.get("package_dir")
        if package_dir:
            owner = seen_package_dirs.setdefault(package_dir, env.name)
            if owner != env.name:
                problems.append(
                    f"{env.name}: loads its datamodel package from {package_dir}, "
                    f"the very directory {owner} uses -- the two environments "
                    "are the same build"
                )

    if manifest.get("environments", {}).get("reference", {}).get("version") not in (
        None, REFERENCE_VERSION
    ):
        problems.append(
            "reference environment does not report version "
            f"{REFERENCE_VERSION!r}"
        )
    return problems


# ---------------------------------------------------------------------------
# Child-process entry point
# ---------------------------------------------------------------------------


def _child_provenance(expect_root: Path) -> Dict[str, Any]:
    """Collected *inside* the child, after ``datamodel`` has been imported."""
    import datamodel  # noqa: PLC0415 - deliberately late

    loaded = Path(datamodel.__file__).resolve()
    if expect_root not in loaded.parents:
        raise _ChildProvenanceError(
            f"imported datamodel from {loaded}, which is not under {expect_root}. "
            "The environment is not isolated: it is loading another build's "
            "compiled artifact."
        )

    package_dir = loaded.parent

    # Every `datamodel.*` module must come from the SAME tree. An editable
    # install registers a meta-path finder that resolves submodules by their
    # full dotted name, so `datamodel` can come from one root while
    # `datamodel.converters` quietly comes from another -- a mixed environment
    # whose measurements and comparisons would both be meaningless. Filtering
    # such a module out of the digest list would hide exactly the fault this
    # manifest exists to detect, so it is a hard error.
    binaries: Dict[str, str] = {}
    strays: List[str] = []
    for name, module in sorted(sys.modules.items()):
        if name != "datamodel" and not name.startswith("datamodel."):
            continue
        origin = getattr(module, "__file__", None)
        if not origin:
            continue  # namespace package, nothing to attribute
        origin_path = Path(origin).resolve()
        if package_dir not in origin_path.parents:
            strays.append(f"{name} -> {origin_path}")
            continue
        if origin_path.suffix in (".so", ".pyd"):
            binaries[origin_path.name] = _sha256(origin_path)
    if strays:
        raise _ChildProvenanceError(
            "the environment is not isolated: these datamodel modules were "
            f"loaded from outside {package_dir}: " + "; ".join(sorted(strays))
        )
    if not binaries:
        raise _ChildProvenanceError(
            f"no compiled datamodel extensions were loaded from {package_dir}; "
            "the environment has not been built (run `uv pip install -e .`)"
        )

    try:
        version = datamodel.version.__version__
    except AttributeError:  # pragma: no cover - defensive
        version = None

    try:
        from datamodel.rs_parsers import HAS_RUST
    except Exception:  # pragma: no cover - defensive
        HAS_RUST = None

    return {
        "root": str(expect_root),
        "datamodel_file": str(loaded),
        "package_dir": str(package_dir),
        "version": version,
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": sys.platform,
        "has_rust_parsers": HAS_RUST,
        "binaries": binaries,
        "dependencies": _dependency_versions(),
    }


class _ChildProvenanceError(RuntimeError):
    """In-child twin of :class:`ProvenanceError` (re-raised in the parent)."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dependency_versions() -> Dict[str, Optional[str]]:
    from importlib.metadata import PackageNotFoundError, version as _version

    names = ("Cython", "orjson", "ciso8601", "numpy", "msgspec", "python-dateutil")
    out: Dict[str, Optional[str]] = {}
    for name in names:
        try:
            out[name] = _version(name)
        except PackageNotFoundError:
            out[name] = None
    return out


def _child_import_binaries() -> None:
    """Import the compiled modules so their hashes appear in the provenance."""
    import datamodel.converters  # noqa: F401
    import datamodel.exceptions  # noqa: F401
    import datamodel.fields  # noqa: F401
    import datamodel.validation  # noqa: F401
    import datamodel.parsers.json  # noqa: F401


def _child_run_cases(case_names: Optional[List[str]]) -> Dict[str, Dict[str, Any]]:
    """Build each requested case **exactly once** and observe the result.

    Building once is not an optimisation: a case may invoke user callbacks, and
    running them twice would both corrupt the callback-count comparison and
    (in a real consumer's fixtures) repeat a side effect.
    """
    from tests.compatibility.observations import FORMAT_VERSION, Observer
    from tests.fixtures.model_performance import cases as cases_mod
    from tests.fixtures.model_performance import models as models_mod

    selected = cases_mod.CASES
    if case_names is not None:
        wanted = list(case_names)
        missing = [name for name in wanted if name not in cases_mod.CASES_BY_NAME]
        if missing:
            raise KeyError(f"unknown case(s): {missing}")
        selected = tuple(cases_mod.CASES_BY_NAME[name] for name in wanted)

    results: Dict[str, Dict[str, Any]] = {}
    for case in selected:
        results[case.name] = _child_run_case(
            case, cases_mod, models_mod, Observer, FORMAT_VERSION
        )
    return results


def _child_run_case(case, cases_mod, models_mod, Observer, format_version):
    observer = Observer()
    models_mod.reset_hook_events()

    kwargs = cases_mod.build_kwargs(case)
    # Observed with the *same* observer as everything else, so an argument that
    # survives into a field is reported as the same reference number.
    before = observer.observe(kwargs)

    record: Dict[str, Any] = {
        "format_version": format_version,
        "case": case.name,
        "model": case.model_name,
        "declared_expectation": case.expect,
        "input_before": before,
    }

    try:
        instance = case.resolve_model()(**kwargs)
    except BaseException as exc:  # noqa: BLE001 - the exception *is* the result
        record["outcome"] = "error"
        record["error"] = _observe_exception(exc, observer)
        record["instance"] = None
        record["fresh_results"] = None
    else:
        record["outcome"] = "ok"
        record["error"] = None
        record["instance"] = observer.observe(instance)
        record["fresh_results"] = _observe_fresh_results(instance, observer)

    # After construction: did the constructor mutate the caller's input?
    record["input_after"] = observer.observe(kwargs)
    record["callbacks"] = [
        [name, observer.observe(payload)] for name, payload in models_mod.hook_events
    ]
    record["callback_counts"] = _counts(name for name, _ in models_mod.hook_events)
    models_mod.reset_hook_events()
    return record


def _counts(names: Iterable[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for name in names:
        out[name] = out.get(name, 0) + 1
    return out


def _observe_exception(exc: BaseException, observer) -> Dict[str, Any]:
    """Type, message, payload and cause — the whole observable error contract."""
    record: Dict[str, Any] = {
        "type": type(exc).__name__,
        "module": type(exc).__module__,
        "message": str(exc),
        "args": [observer.observe(arg) for arg in getattr(exc, "args", ())],
        "payload": None,
        "cause": None,
        "context": None,
    }
    payload = getattr(exc, "payload", None)
    if payload is not None:
        record["payload"] = observer.observe(payload)
        # Payload *order* is part of ValidationError's string output
        # (exceptions.pyx:24-38), so it is compared explicitly.
        if isinstance(payload, dict):
            record["payload_order"] = list(payload.keys())
    cause = exc.__cause__
    if cause is not None:
        record["cause"] = {"type": type(cause).__name__,
                           "module": type(cause).__module__,
                           "message": str(cause)}
    context = exc.__context__
    if context is not None and context is not cause:
        record["context"] = {"type": type(context).__name__,
                             "module": type(context).__module__,
                             "message": str(context)}
    return record


def _observe_fresh_results(instance: Any, observer) -> Dict[str, Any]:
    """Do externally callable dictionary results stay independently mutable?

    ``to_dict`` must hand back a *fresh* mapping on every call; returning a
    shared object would be observable to a consumer.  The check is expressed as
    a relationship (are the two calls the same object?) so it survives the
    process boundary.
    """
    to_dict = getattr(instance, "to_dict", None)
    if not callable(to_dict):
        return {"supported": False}
    try:
        first = to_dict()
        second = to_dict()
    except Exception as exc:  # noqa: BLE001 - a failing to_dict is an observation
        return {"supported": True, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "supported": True,
        "error": None,
        "same_object": first is second,
        "equal": first == second,
        "keys": list(first) if isinstance(first, dict) else None,
    }


def _worker_main() -> int:
    request = json.loads(sys.stdin.read())
    expect_root = Path(request["expect_root"]).resolve()
    harness_root = Path(request["harness_root"]).resolve()

    try:
        # 1. Bind `datamodel` from THIS environment, before anything else can.
        sys.path.insert(0, str(expect_root))
        import datamodel  # noqa: F401,PLC0415

        _child_import_binaries()
        provenance = _child_provenance(expect_root)

        # 2. Only now make the shared harness importable.  `datamodel` is
        #    already in sys.modules, so the fixtures cannot re-bind it.
        #    `expect_root` is *removed* first: the reference worktree has its
        #    own regular `tests` package, and a regular package's __path__ is
        #    fixed at import time, so leaving it ahead of the harness would
        #    make `tests.fixtures.model_performance` unimportable.
        while str(expect_root) in sys.path:
            sys.path.remove(str(expect_root))
        sys.path.insert(0, str(harness_root))

        payload: Dict[str, Any] = {"provenance": provenance, "error": None}
        if request["mode"] == "run":
            payload["cases"] = _child_run_cases(request.get("cases"))
        else:
            payload["cases"] = {}
    except _ChildProvenanceError as exc:
        payload = {"error": {"type": "ProvenanceError", "message": str(exc)}}
    except BaseException as exc:  # noqa: BLE001 - report, never crash silently
        import traceback

        payload = {
            "error": {
                "type": type(exc).__name__,
                "message": f"{exc}\n{traceback.format_exc()}",
            }
        }

    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()
    return 0


def _cli_main(argv: Sequence[str]) -> int:
    if "--write-manifest" in argv:
        environments = [candidate_environment()]
        reference = reference_environment()
        if reference is None:
            print(
                "reference environment not found; set "
                f"${REFERENCE_ROOT_ENV} or create a worktree at "
                f"../{DEFAULT_REFERENCE_DIRNAME}",
                file=sys.stderr,
            )
            return 2
        environments.insert(0, reference)
        manifest = write_manifest(environments)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    if sys.stdin.isatty() or len(sys.argv) > 1:
        raise SystemExit(_cli_main(sys.argv[1:]))
    raise SystemExit(_worker_main())
