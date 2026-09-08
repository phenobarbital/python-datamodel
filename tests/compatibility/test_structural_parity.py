"""Structural invariants around construction cost (FEAT-2 / TASK-15).

TASK-15 profiled what remains after the TASK-13 gate and reached a **negative
result**: the two largest remaining savings -- reusing the per-build column
snapshot, and replacing the ``__fields__`` list scan with a set -- are both
unsafe, and the safe alternatives measured as no change.  The full evidence is
in ``benchmarks/results/compatible-model-performance/structural.json``.

The lasting value of that work is *these tests*.  Each one pins the specific
observable behaviour that makes an attractive optimisation unsafe, so a future
attempt fails loudly instead of shipping a subtle regression.  They are written
against behaviour, not against the current implementation, and the ones that
matter most are verified against the 0.10.21 reference too.

If you are here because you want to make construction faster: read the verdicts
in ``structural.json`` first, then make one of these tests fail honestly before
you change anything.
"""
import sys
from pathlib import Path

import pytest

from datamodel import BaseModel, Column

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.compatibility.test_mutation_parity import assert_parity  # noqa: E402

STRUCTURAL_REPORT = (
    Path(__file__).resolve().parents[2]
    / "benchmarks" / "results" / "compatible-model-performance" / "structural.json"
)


# ===========================================================================
# Part 1 -- why the column snapshot cannot be replaced by a live view (A1)
# ===========================================================================


def test_a_callback_may_mutate_columns_during_processing():
    """`__post_init__` iterates a COPY, and that is load-bearing.

    An encoder that inserts a new column while `processing_fields` is running
    works today. Passing the live `__columns__.items()` view instead of a
    snapshot would turn this into `RuntimeError: dictionary changed size
    during iteration` -- a silent regression bought for about 2%.
    """
    class Mutator(BaseModel):
        v: float = Column(
            required=False,
            encoder=lambda value: (
                Mutator.__columns__.__setitem__(
                    "injected", Mutator.__columns__["v"]
                ),
                float(value),
            )[1],
        )

        class Meta:
            strict = False

    instance = Mutator(v=1)
    assert instance.v == 1.0
    assert "injected" in Mutator.__columns__


def test_a_callback_may_mutate_columns_on_both_builds():
    """The same tolerance must hold on the 0.10.21 reference."""
    assert_parity({
        "columns_mutated_during_processing": '''
def run():
    class M(BaseModel):
        v: float = Column(
            required=False,
            encoder=lambda value: (
                M.__columns__.__setitem__("injected", M.__columns__["v"]),
                float(value))[1])
        class Meta:
            strict = False
    return {"value": attempt(lambda: M(v=1).v),
            "injected": describe("injected" in M.__columns__)}
''',
    })


def test_removing_a_column_mid_build_does_not_corrupt_the_rest():
    class Remover(BaseModel):
        first: float = Column(
            required=False,
            encoder=lambda value: (
                Remover.__columns__.pop("volatile", None), float(value)
            )[1],
        )
        volatile: int = Column(required=False)

        class Meta:
            strict = False

    instance = Remover(first=1, volatile=2)
    assert instance.first == 1.0


# ===========================================================================
# Part 2 -- why membership cannot be cached in a set (B)
# ===========================================================================


def test_public_fields_list_mutation_is_honoured():
    """`__fields__` is public, mutable, and consulted live.

    A parallel set built at class creation would not see this append, and the
    assignment would be misrouted to the extra-attribute path.
    """
    class Extendable(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False
            extra = "allow"

    instance = Extendable(known=1)
    Extendable.__fields__.append("manual")
    instance.manual = 7
    assert instance.manual == 7


def test_fields_and_columns_are_not_interchangeable():
    """Using `__columns__` for membership instead would also be wrong.

    The two containers genuinely diverge, in both directions:

    * appending to `__fields__` does not create a column;
    * `BaseModel.add_field` inserts into `__columns__` and
      `__dataclass_fields__` **without** touching `__fields__`.

    (`create_field` is *not* an example: it ends with `setattr`, which routes
    through `_dc_method_setattr_` and appends to `__fields__` as a side
    effect. I asserted otherwise at first and the test caught me.)
    """
    class Diverging(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False
            extra = "allow"

    Diverging.__fields__.append("only_in_fields")
    assert "only_in_fields" not in Diverging.__columns__

    Diverging.add_field("only_in_columns", 5)
    assert "only_in_columns" in Diverging.__columns__
    assert "only_in_columns" not in Diverging.__fields__


def test_add_field_leaves_the_class_unconstructible():
    """CHARACTERIZATION of a pre-existing quirk, identical on both builds.

    `add_field` registers a column that `processing_fields` then tries to read
    with `getattr`, but never installs a value or adds the name to
    `__fields__` -- so the very next construction raises AttributeError.
    Verified on 0.10.21 as well, so it is not something this feature
    introduced. Pinned here because a future membership optimisation that
    "helpfully" reconciled the two containers would silently change it.
    """
    class Broken(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False

    Broken.add_field("orphan", 5)
    with pytest.raises(AttributeError):
        Broken(known=1)


def test_a_property_setter_may_register_its_own_field():
    """REGRESSION. `object.__setattr__` is not inert -- it runs descriptors.

    TASK-15 removed a second `if name not in self.__fields__:` guard from
    `_dc_method_setattr_` as "provably redundant, nothing between the two
    checks can mutate __fields__". That reasoning was WRONG: the
    `object.__setattr__` between them consults the type's data descriptors, so
    a class-level `property` setter runs arbitrary user code -- which may
    legitimately append its own name to `__fields__`.

    With the guard removed, this raised `TypeError: Field 'dynamic' is not
    allowed`, while the 0.10.21 reference accepted the assignment. Found by
    adversarial review, verified against the reference, and the guard restored.
    """
    class SelfRegistering(BaseModel):
        known: int = Column(required=False, default=0)

        class Meta:
            strict = False
            extra = "forbid"

        @property
        def dynamic(self):
            return self.__dict__.get("dynamic")

        @dynamic.setter
        def dynamic(self, value):
            self.__dict__["dynamic"] = value
            if "dynamic" not in self.__fields__:
                self.__fields__.append("dynamic")

    instance = SelfRegistering(known=1)
    instance.dynamic = 42
    assert instance.dynamic == 42
    assert "dynamic" in SelfRegistering.__fields__


def test_a_property_setter_registering_its_field_agrees_with_the_reference():
    assert_parity({
        "self_registering_property": '''
def run():
    class M(BaseModel):
        known: int = Column(required=False, default=0)
        class Meta:
            strict = False
            extra = "forbid"
        @property
        def dynamic(self):
            return self.__dict__.get("dynamic")
        @dynamic.setter
        def dynamic(self, value):
            self.__dict__["dynamic"] = value
            if "dynamic" not in self.__fields__:
                self.__fields__.append("dynamic")
    instance = M(known=1)
    def assign():
        instance.dynamic = 42
        return instance.dynamic
    return {"result": attempt(assign),
            "in_fields": describe("dynamic" in M.__fields__)}
''',
    })


def test_public_fields_mutation_is_honoured_on_both_builds():
    assert_parity({
        "public_fields_append": '''
def run():
    class M(BaseModel):
        known: int = Column(required=False)
        class Meta:
            strict = False
            extra = "allow"
    instance = M(known=1)
    M.__fields__.append("manual")
    instance.manual = 7
    return {"manual": attempt(lambda: instance.manual),
            "in_columns": describe("manual" in M.__columns__)}
''',
    })


def test_dynamically_added_field_becomes_a_known_field():
    """The extra-attribute path appends to `__fields__` as it goes.

    This is why removing the redundant second guard (candidate C) has no
    measurable effect: after the first assignment the name is known, and
    every later assignment takes the early branch.
    """
    class Growing(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False
            extra = "allow"

    instance = Growing(known=1)
    assert "added" not in Growing.__fields__
    instance.added = 5
    assert "added" in Growing.__fields__
    instance.added = 6
    assert instance.added == 6


# ===========================================================================
# Part 3 -- the invariants the removed guard must not have disturbed (C)
# ===========================================================================


def test_strict_model_still_rejects_unknown_attributes():
    class Strict(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = True

    instance = Strict(known=1)
    instance.surprise = 5
    assert "surprise" not in Strict.__fields__


def test_extra_forbid_still_raises():
    class Forbidding(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False
            extra = "forbid"

    instance = Forbidding(known=1)
    with pytest.raises(TypeError):
        instance.surprise = 5


def test_extra_ignore_still_ignores():
    class Ignoring(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False
            extra = "ignore"

    instance = Ignoring(known=1)
    instance.surprise = 5
    assert "surprise" not in Ignoring.__fields__


def test_dunder_assignment_still_bypasses_field_handling():
    class Plain(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False

    instance = Plain(known=1)
    object.__setattr__(instance, "__custom__", 1)
    instance.__custom__ = 2
    assert instance.__custom__ == 2
    assert "__custom__" not in Plain.__fields__


def test_extra_attribute_paths_agree_with_the_reference():
    assert_parity({
        "extra_policies": '''
def run():
    out = {}
    for policy in ("allow", "ignore", "forbid"):
        class M(BaseModel):
            known: int = Column(required=False)
            class Meta:
                strict = False
        M.Meta.extra = policy
        instance = M(known=1)
        def assign():
            instance.surprise = 5
            return instance.surprise
        out[policy] = attempt(assign)
        out[policy + "_in_fields"] = describe("surprise" in M.__fields__)
    return out
''',
        "strict_extra": '''
def run():
    class M(BaseModel):
        known: int = Column(required=False)
        class Meta:
            strict = True
    instance = M(known=1)
    def assign():
        instance.surprise = 5
        return "surprise" in M.__fields__
    return {"result": attempt(assign)}
''',
    })


# ===========================================================================
# Part 4 -- values, history and aliases survive
# ===========================================================================


def test_values_and_old_value_are_unchanged():
    class Tracked(BaseModel):
        v: int = Column(required=False)

        class Meta:
            strict = False

    instance = Tracked(v=1)
    instance.v = 2
    assert instance.v == 2
    assert instance.old_value("v") == 1


def test_aliases_still_resolve():
    class Aliased(BaseModel):
        value: str = Column(required=False, alias="wire")

        class Meta:
            strict = False

    assert Aliased(value="a").value == "a"
    assert Aliased(wire="b").value == "b"


def test_fifty_field_model_still_builds_and_scales():
    """50-field scaling is where an O(n) membership scan would hurt most.

    It is asserted to still *work*; the measurement of what it costs, and why
    the scan was left alone, is in structural.json.
    """
    annotations = {f"f{i}": int for i in range(50)}
    attributes = {name: Column(required=False, default=0) for name in annotations}
    attributes["__annotations__"] = annotations
    Wide = type("WideStructural", (BaseModel,), attributes)

    instance = Wide(**{f"f{i}": i for i in range(50)})
    assert instance.f0 == 0
    assert instance.f49 == 49
    assert len(instance.to_dict()) == 50


# ===========================================================================
# Part 5 -- the report itself is honest
# ===========================================================================


def test_structural_report_exists_and_records_every_verdict():
    import json

    assert STRUCTURAL_REPORT.is_file(), f"{STRUCTURAL_REPORT} is missing"
    report = json.loads(STRUCTURAL_REPORT.read_text(encoding="utf-8"))

    verdicts = {c["id"]: c["verdict"] for c in report["candidates"]}
    assert set(verdicts) == {"A1", "A2", "B", "C", "D", "E"}
    for identifier, verdict in verdicts.items():
        assert verdict.startswith(("REJECTED", "APPLIED", "RETRACTED")), (
            identifier, verdict
        )
        candidate = next(c for c in report["candidates"] if c["id"] == identifier)
        assert candidate.get("reason") or candidate.get("honest_note"), identifier


def test_structural_report_records_the_retraction():
    """Candidate C was applied, then proven wrong, then reverted.

    The report must keep saying so. Quietly dropping a retracted candidate --
    or downgrading it to a plain REJECTED as though it had never shipped --
    would erase the most instructive part of this task: that "provable from
    control flow" was asserted without accounting for descriptor reentrancy
    through `object.__setattr__`, and a code review caught it rather than the
    test suite.
    """
    import json

    report = json.loads(STRUCTURAL_REPORT.read_text(encoding="utf-8"))
    candidate = next(c for c in report["candidates"] if c["id"] == "C")
    assert candidate["verdict"].startswith("RETRACTED"), candidate["verdict"]
    assert "descriptor" in candidate["reason"].lower()
    assert "0.10.21" in candidate["reason"]


def test_structural_report_does_not_claim_an_unmeasured_win():
    """No candidate may be dressed up as a speed-up.

    Every candidate is now rejected or retracted, so the report must not
    contain an APPLIED verdict at all.
    """
    import json

    report = json.loads(STRUCTURAL_REPORT.read_text(encoding="utf-8"))
    applied = [c for c in report["candidates"] if c["verdict"].startswith("APPLIED")]
    assert not applied, (
        f"the report claims changes were applied, but this task ended with no "
        f"production change: {[c['id'] for c in applied]}"
    )
    assert "NEGATIVE RESULT" in report["headline"]
