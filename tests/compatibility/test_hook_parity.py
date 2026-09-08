"""Callback and hook parity across the validation gate (FEAT-2 / TASK-14).

The gate in ``processing_fields`` sits *after* conversion and *after* user
callbacks have run.  That placement is load-bearing: a callback may mutate the
field it is attached to, or a later field, and the validator must see the
mutated state.  It is also fragile in one specific way -- if the gate skipped a
dispatch, a callback that the legacy path would have invoked might never run,
or might run a different number of times.

So the assertions here are about **order and count**, not just final values,
including the case the acceptance criteria call out explicitly: callbacks must
still execute identically *when an earlier field has already failed*.

Every scenario runs in both the 0.10.21 reference and the candidate, and the
two must agree.  The harness lives in ``test_mutation_parity.py``; all three
files belong to this task.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.compatibility.test_mutation_parity import assert_parity  # noqa: E402


ENCODER_SCENARIOS = {
    # A live encoder route (float). The str encoder route is dead on both
    # builds -- see TASK-7 -- so it would prove nothing here.
    "encoder_call_count": '''
def run():
    calls = []
    class M(BaseModel):
        v: float = Column(required=False,
                          encoder=lambda value: (calls.append(value), float(value))[1])
        class Meta:
            strict = False
    instance = M(v=2)
    return {"value": attempt(lambda: instance.v), "calls": describe(calls)}
''',
    "encoder_runs_when_an_earlier_field_fails": '''
def run():
    calls = []
    class M(BaseModel):
        bad: int = Column(required=False, max=10)
        later: float = Column(required=False,
                              encoder=lambda value: (calls.append(value), float(value))[1])
        class Meta:
            strict = False
    instance = M(bad=99, later=3)
    return {"errors": describe(sorted(instance.get_errors() or {})),
            "calls": describe(calls),
            "later": attempt(lambda: instance.later)}
''',
    "encoder_raising_is_reported": '''
def run():
    def boom(value):
        raise ValueError("encoder exploded")
    class M(BaseModel):
        v: float = Column(required=False, encoder=boom)
        class Meta:
            strict = False
    return {"result": attempt(lambda: M(v=1))}
''',
    "dead_str_encoder_stays_dead": '''
def run():
    calls = []
    class M(BaseModel):
        s: str = Column(required=False,
                        encoder=lambda value: (calls.append(value), str(value))[1])
        class Meta:
            strict = False
    instance = M(s="x")
    return {"value": attempt(lambda: instance.s), "calls": describe(calls)}
''',
}

VALIDATOR_SCENARIOS = {
    "dead_primitive_validator_stays_dead": '''
def run():
    calls = []
    def validator(field, value, annotated_type, val_type):
        calls.append(value)
        return True
    class M(BaseModel):
        v: int = Column(required=False, validator=validator)
        class Meta:
            strict = False
    instance = M(v=1)
    return {"value": attempt(lambda: instance.v), "calls": describe(calls)}
''',
    "live_container_validator_runs": '''
def run():
    from typing import List
    calls = []
    def validator(field, value, annotated_type, val_type):
        calls.append(describe(value))
        return True
    class M(BaseModel):
        v: List[str] = Column(required=False, validator=validator)
        class Meta:
            strict = False
    instance = M(v=["a", "b"])
    return {"value": attempt(lambda: instance.v), "calls": describe(len(calls))}
''',
    "validator_returning_false_is_an_error": '''
def run():
    from typing import List
    class M(BaseModel):
        v: List[str] = Column(
            required=False,
            validator=lambda field, value, annotated_type, val_type: False)
        class Meta:
            strict = False
    return {"result": attempt(lambda: (M(v=["a"]).get_errors() or {}))}
''',
}

POST_INIT_SCENARIOS = {
    "post_init_runs_once": '''
def run():
    events = []
    class M(BaseModel):
        v: int = Column(required=False)
        def __post_init__(self):
            events.append("hook")
            super().__post_init__()
        class Meta:
            strict = False
    instance = M(v=1)
    return {"events": describe(events), "value": attempt(lambda: instance.v)}
''',
    "post_init_mutating_its_own_field": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False, max=10)
        def __post_init__(self):
            self.__dict__["v"] = 99
            super().__post_init__()
        class Meta:
            strict = False
    instance = M(v=1)
    return {"value": attempt(lambda: instance.v),
            "errors": describe(sorted(instance.get_errors() or {}))}
''',
    "post_init_mutating_a_later_field": '''
def run():
    class M(BaseModel):
        first: int = Column(required=False)
        second: int = Column(required=False, max=10)
        def __post_init__(self):
            self.__dict__["second"] = 99
            super().__post_init__()
        class Meta:
            strict = False
    instance = M(first=1, second=1)
    return {"second": attempt(lambda: instance.second),
            "errors": describe(sorted(instance.get_errors() or {}))}
''',
    "post_init_raising": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        def __post_init__(self):
            super().__post_init__()
            raise ValueError("hook exploded")
        class Meta:
            strict = False
    return {"result": attempt(lambda: M(v=1))}
''',
    "post_init_adding_metadata_mid_flight": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        def __post_init__(self):
            field = self.__columns__["v"]
            field._meta["max"] = 10
            field.metadata = field._meta
            super().__post_init__()
        class Meta:
            strict = False
    first = attempt(lambda: (M(v=99).get_errors() or {}))
    second = attempt(lambda: (M(v=99).get_errors() or {}))
    return {"first": first, "second": second}
''',
}

DESCRIPTOR_SCENARIOS = {
    "descriptor_field": '''
def run():
    class Upper:
        def __init__(self):
            self.value = None
        def __set_name__(self, owner, name):
            self.name = name
        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            return obj.__dict__.get(self.name)
        def __set__(self, obj, value):
            obj.__dict__[self.name] = value.upper() if isinstance(value, str) else value
    class M(BaseModel):
        plain: str = Column(required=False)
        class Meta:
            strict = False
    M.described = Upper()
    M.described.__set_name__(M, "described")
    instance = M(plain="x")
    instance.described = "abc"
    return {"plain": attempt(lambda: instance.plain),
            "described": attempt(lambda: instance.described)}
''',
    "assignment_history_after_build": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    instance = M(v=1)
    instance.v = 2
    out = {"value": attempt(lambda: instance.v),
           "to_dict": attempt(lambda: instance.to_dict())}
    out["old_value"] = attempt(lambda: instance.old_value("v"))
    return out
''',
    "reset_values_round_trip": '''
def run():
    class M(BaseModel):
        v: int = Column(required=False, default=1)
        class Meta:
            strict = False
    instance = M(v=5)
    instance.v = 7
    before = attempt(lambda: instance.v)
    reset = attempt(lambda: instance.reset_values())
    return {"before": before, "reset": reset,
            "after": attempt(lambda: instance.v)}
''',
}


def test_encoder_parity():
    """Encoder call counts and ordering, including after an earlier failure."""
    assert_parity(ENCODER_SCENARIOS)


def test_validator_callback_parity():
    """Built-in versus metadata callback routes must stay distinguishable."""
    assert_parity(VALIDATOR_SCENARIOS)


def test_post_init_parity():
    """The gate observes post-callback state on both builds."""
    assert_parity(POST_INIT_SCENARIOS)


def test_descriptor_and_assignment_parity():
    assert_parity(DESCRIPTOR_SCENARIOS)


def test_callback_order_is_identical_with_a_failing_field():
    """AC: identical order AND count even when an earlier field fails."""
    scenarios = {
        "ordered_callbacks": '''
def run():
    order = []
    def make(tag):
        def encoder(value):
            order.append(tag)
            return float(value)
        return encoder
    class M(BaseModel):
        first: float = Column(required=False, encoder=make("first"))
        broken: int = Column(required=False, max=10)
        third: float = Column(required=False, encoder=make("third"))
        class Meta:
            strict = False
    instance = M(first=1, broken=99, third=3)
    return {"order": describe(order),
            "errors": describe(sorted(instance.get_errors() or {}))}
''',
        "ordered_callbacks_all_valid": '''
def run():
    order = []
    def make(tag):
        def encoder(value):
            order.append(tag)
            return float(value)
        return encoder
    class M(BaseModel):
        first: float = Column(required=False, encoder=make("first"))
        broken: int = Column(required=False, max=10)
        third: float = Column(required=False, encoder=make("third"))
        class Meta:
            strict = False
    instance = M(first=1, broken=5, third=3)
    return {"order": describe(order),
            "errors": describe(sorted(instance.get_errors() or {}))}
''',
    }
    assert_parity(scenarios)
