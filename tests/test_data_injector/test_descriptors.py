# tests/test_data_injector/test_descriptors.py
import pytest

from pyre.data_injector.descriptors import FieldDescriptor
from pyre.data_injector.exceptions import InjectionError


class TestFieldDescriptorDefaults:
    def test_source_key_defaults_to_name(self):
        fd = FieldDescriptor(name="premium")
        assert fd.source_key == "premium"

    def test_explicit_source_key(self):
        fd = FieldDescriptor(name="premium", source_key="gross_premium")
        assert fd.source_key == "gross_premium"


class TestGetValue:
    def test_extracts_value_from_record(self):
        fd = FieldDescriptor(name="x")
        assert fd.get_value({"x": 42}) == 42

    def test_uses_source_key_not_name(self):
        fd = FieldDescriptor(name="premium", source_key="gross")
        assert fd.get_value({"gross": 99.0}) == 99.0

    def test_missing_required_raises(self):
        fd = FieldDescriptor(name="x", required=True)
        with pytest.raises(InjectionError, match="Required field 'x'"):
            fd.get_value({})

    def test_missing_optional_returns_none(self):
        fd = FieldDescriptor(name="x", required=False)
        assert fd.get_value({}) is None

    def test_missing_uses_static_default(self):
        fd = FieldDescriptor(name="x", default="fallback")
        assert fd.get_value({}) == "fallback"

    def test_missing_uses_default_factory(self):
        fd = FieldDescriptor(name="tags", default_factory=list)
        result = fd.get_value({})
        assert result == []
        # Factory is called fresh each time
        assert fd.get_value({}) is not fd.get_value({})


class TestCoercion:
    def test_coerces_str_to_int(self):
        fd = FieldDescriptor(name="x", type_coerce=int)
        assert fd.get_value({"x": "42"}) == 42

    def test_coerces_str_to_float(self):
        fd = FieldDescriptor(name="x", type_coerce=float)
        assert fd.get_value({"x": "3.14"}) == pytest.approx(3.14)

    def test_skips_coercion_if_already_correct_type(self):
        fd = FieldDescriptor(name="x", type_coerce=int)
        assert fd.get_value({"x": 7}) == 7

    def test_bad_coercion_raises_injection_error(self):
        fd = FieldDescriptor(name="x", type_coerce=int)
        with pytest.raises(InjectionError, match="cannot coerce"):
            fd.get_value({"x": "not_a_number"})

    def test_callable_coerce(self):
        from datetime import date

        fd = FieldDescriptor(name="d", type_coerce=date.fromisoformat)
        assert fd.get_value({"d": "2024-01-15"}) == date(2024, 1, 15)


class TestPreProcessAndValidator:
    def test_pre_process_runs_before_coerce(self):
        fd = FieldDescriptor(
            name="x",
            pre_process=str.strip,
            type_coerce=int,
        )
        assert fd.get_value({"x": "  7  "}) == 7

    def test_validator_called_with_final_value(self):
        called_with: list = []

        def record_call(v: int) -> None:
            called_with.append(v)

        fd = FieldDescriptor(name="x", validator=record_call)
        fd.get_value({"x": 5})
        assert called_with == [5]

    def test_validator_failure_raises_injection_error(self):
        def must_be_positive(v: float) -> None:
            if v <= 0:
                raise ValueError("Must be positive")

        fd = FieldDescriptor(name="x", type_coerce=float, validator=must_be_positive)
        with pytest.raises(InjectionError, match="failed validation"):
            fd.get_value({"x": "-1"})
