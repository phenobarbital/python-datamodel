"""Deterministic model-compatibility fixtures for FEAT-2.

This package holds the reference corpus used by the differential
reference/candidate runner and by the paired performance harness.

Design rules (spec ``sdd/specs/compatible-model-performance.spec.md`` §4):

* Every case builds **independent mutable inputs** on each call, so a model
  mutated by one backend can never be observed by the other.
* Deliberate aliases *within* a single case are preserved, because alias
  relationships are part of the observed behaviour.
* No clock, randomness, filesystem, network or database access happens while
  a case is built: nondeterministic factories are stubbed with frozen values.
* Only ``datamodel``'s long-standing public surface (``BaseModel``, ``Field``,
  ``Column``, ``ValidationError``) is used, so the very same module imports
  cleanly against both the engineering reference (0.10.21) and the candidate.
"""
from .models import (  # noqa: F401
    ALL_MODELS,
    Account,
    Address,
    AliasedRecord,
    BigContainer,
    Boundaries,
    CallbackModel,
    Client,
    ConstrainedScalars,
    DescriptorModel,
    Employee,
    HookModel,
    Organization,
    PresenceRules,
    UnconstrainedScalars,
    WideModel,
    hook_events,
    reset_hook_events,
)
from .cases import (  # noqa: F401
    CASES,
    CASES_BY_NAME,
    Case,
    case_names,
    cases_with_tag,
)

__all__ = (
    "ALL_MODELS",
    "Account",
    "Address",
    "AliasedRecord",
    "BigContainer",
    "Boundaries",
    "CASES",
    "CASES_BY_NAME",
    "CallbackModel",
    "Case",
    "Client",
    "ConstrainedScalars",
    "DescriptorModel",
    "Employee",
    "HookModel",
    "Organization",
    "PresenceRules",
    "UnconstrainedScalars",
    "WideModel",
    "case_names",
    "cases_with_tag",
    "hook_events",
    "reset_hook_events",
)
