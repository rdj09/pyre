# Data Injector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pyre.data_injector` — a production-ready, extensible library that maps external data (JSON, CSV, YAML, Excel, dicts) into typed Python dataclass instances with validation, type coercion, and nested object support.

**Architecture:** A two-phase pipeline: Source Adapters normalise raw inputs into `list[dict[str, Any]]`, then an Injector walks a Schema of FieldDescriptors to construct typed instances. A Loader facade combines adapter selection and injection into a single call per source type. An AdapterRegistry enables plugin-style extension with zero changes to core code.

**Tech Stack:** Python 3.10+, stdlib only for core (`dataclasses`, `json`, `csv`, `pathlib`); optional extras `pyyaml` and `openpyxl` for YAML/Excel adapters; `pytest` for tests.

---

## File Map

| File | Responsibility |
|---|---|
| `src/pyre/data_injector/__init__.py` | Public API re-exports |
| `src/pyre/data_injector/exceptions.py` | `InjectionError` |
| `src/pyre/data_injector/utils.py` | `unflatten()`, `parse_bool()`, `parse_list()` |
| `src/pyre/data_injector/descriptors.py` | `FieldDescriptor` — rename, coerce, default, validate |
| `src/pyre/data_injector/schema.py` | `Schema[T]` — field list, nested schemas, hooks |
| `src/pyre/data_injector/injector.py` | `Injector[T]` — walks schema, constructs instances |
| `src/pyre/data_injector/loader.py` | `Loader[T]` — facade combining adapter + injector |
| `src/pyre/data_injector/registry.py` | `AdapterRegistry` — plugin registration by name |
| `src/pyre/data_injector/adapters/__init__.py` | Empty |
| `src/pyre/data_injector/adapters/base.py` | `SourceAdapter` Protocol |
| `src/pyre/data_injector/adapters/dict_adapter.py` | `DictAdapter` |
| `src/pyre/data_injector/adapters/json_adapter.py` | `JSONAdapter` |
| `src/pyre/data_injector/adapters/csv_adapter.py` | `CSVAdapter` |
| `src/pyre/data_injector/adapters/yaml_adapter.py` | `YAMLAdapter` |
| `src/pyre/data_injector/adapters/excel_adapter.py` | `ExcelAdapter` |
| `tests/test_data_injector/__init__.py` | Empty |
| `tests/test_data_injector/test_exceptions.py` | InjectionError |
| `tests/test_data_injector/test_utils.py` | unflatten, parse_bool, parse_list |
| `tests/test_data_injector/test_descriptors.py` | FieldDescriptor |
| `tests/test_data_injector/test_schema.py` | Schema, Schema.from_dataclass |
| `tests/test_data_injector/test_injector.py` | Injector flat + nested + errors |
| `tests/test_data_injector/test_adapters.py` | All five adapters |
| `tests/test_data_injector/test_registry.py` | AdapterRegistry |
| `tests/test_data_injector/test_loader.py` | Loader end-to-end |

---

## Task 1: Scaffold package structure and `InjectionError`

**Files:**
- Create: `src/pyre/data_injector/__init__.py`
- Create: `src/pyre/data_injector/exceptions.py`
- Create: `src/pyre/data_injector/adapters/__init__.py`
- Create: `tests/test_data_injector/__init__.py`
- Create: `tests/test_data_injector/test_exceptions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_data_injector/test_exceptions.py
from pyre.data_injector.exceptions import InjectionError


def test_injection_error_is_exception():
    err = InjectionError("field 'x' is missing")
    assert isinstance(err, Exception)
    assert "field 'x' is missing" in str(err)


def test_injection_error_can_chain():
    cause = ValueError("bad value")
    err = InjectionError("coercion failed") from cause
    assert err.__cause__ is cause
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_data_injector/test_exceptions.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyre.data_injector'`

- [ ] **Step 3: Create directory scaffold**

```bash
mkdir -p src/pyre/data_injector/adapters
touch src/pyre/data_injector/__init__.py
touch src/pyre/data_injector/adapters/__init__.py
touch tests/test_data_injector/__init__.py
```

- [ ] **Step 4: Write `exceptions.py`**

```python
# src/pyre/data_injector/exceptions.py


class InjectionError(Exception):
    """Raised when a record cannot be mapped to the target class."""
```

- [ ] **Step 5: Run test to confirm it passes**

```bash
pytest tests/test_data_injector/test_exceptions.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pyre/data_injector/ tests/test_data_injector/
git commit -m "feat(data_injector): scaffold package and InjectionError"
```

---

## Task 2: Utility functions — `unflatten`, `parse_bool`, `parse_list`

**Files:**
- Create: `src/pyre/data_injector/utils.py`
- Create: `tests/test_data_injector/test_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_data_injector/test_utils.py
import pytest
from pyre.data_injector.utils import parse_bool, parse_list, unflatten


class TestUnflatten:
    def test_single_level_key_unchanged(self):
        assert unflatten({"name": "Alice"}) == {"name": "Alice"}

    def test_dot_notation_becomes_nested(self):
        result = unflatten({"address.city": "London", "address.postcode": "EC1"})
        assert result == {"address": {"city": "London", "postcode": "EC1"}}

    def test_three_levels_deep(self):
        result = unflatten({"a.b.c": 42})
        assert result == {"a": {"b": {"c": 42}}}

    def test_mixed_flat_and_nested(self):
        result = unflatten({"name": "Bob", "address.city": "York"})
        assert result == {"name": "Bob", "address": {"city": "York"}}

    def test_empty_dict(self):
        assert unflatten({}) == {}

    def test_custom_separator(self):
        result = unflatten({"address__city": "Leeds"}, separator="__")
        assert result == {"address": {"city": "Leeds"}}


class TestParseBool:
    def test_true_strings(self):
        for val in ("true", "True", "TRUE", "yes", "YES", "1"):
            assert parse_bool(val) is True

    def test_false_strings(self):
        for val in ("false", "False", "FALSE", "no", "NO", "0"):
            assert parse_bool(val) is False

    def test_bool_passthrough(self):
        assert parse_bool(True) is True
        assert parse_bool(False) is False

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_bool("maybe")


class TestParseList:
    def test_csv_string(self):
        assert parse_list()("a, b, c") == ["a", "b", "c"]

    def test_list_passthrough(self):
        assert parse_list()(["x", "y"]) == ["x", "y"]

    def test_custom_separator(self):
        assert parse_list(sep="|")("a|b|c") == ["a", "b", "c"]
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_data_injector/test_utils.py -v
```

Expected: `ImportError: cannot import name 'unflatten'`

- [ ] **Step 3: Write `utils.py`**

```python
# src/pyre/data_injector/utils.py
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def unflatten(record: dict[str, Any], separator: str = ".") -> dict[str, Any]:
    """Expand dot-notation keys into nested dicts.

    {'address.city': 'London'} -> {'address': {'city': 'London'}}
    """
    result: dict[str, Any] = {}
    for key, value in record.items():
        parts = key.split(separator)
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return result


def parse_bool(value: Any) -> bool:
    """Coerce common string representations to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in {"true", "yes", "1"}:
            return True
        if value.lower() in {"false", "no", "0"}:
            return False
    raise ValueError(f"Cannot parse {value!r} as bool")


def parse_list(sep: str = ",") -> Callable[[Any], list[str]]:
    """Return a callable that splits a string on *sep* into a stripped list."""
    def _parse(value: Any) -> list[str]:
        if isinstance(value, list):
            return value
        return [v.strip() for v in str(value).split(sep)]
    return _parse
```

- [ ] **Step 4: Run to confirm all pass**

```bash
pytest tests/test_data_injector/test_utils.py -v
```

Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/data_injector/utils.py tests/test_data_injector/test_utils.py
git commit -m "feat(data_injector): add unflatten, parse_bool, parse_list utilities"
```

---

## Task 3: `FieldDescriptor`

**Files:**
- Create: `src/pyre/data_injector/descriptors.py`
- Create: `tests/test_data_injector/test_descriptors.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_data_injector/test_descriptors.py
from dataclasses import MISSING

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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_data_injector/test_descriptors.py -v
```

Expected: `ImportError: cannot import name 'FieldDescriptor'`

- [ ] **Step 3: Write `descriptors.py`**

```python
# src/pyre/data_injector/descriptors.py
from __future__ import annotations

from collections.abc import Callable
from dataclasses import MISSING, dataclass
from typing import Any

from .exceptions import InjectionError


@dataclass
class FieldDescriptor:
    """Declares how one field is sourced, coerced, and validated.

    Attributes:
        name:            Target class attribute name.
        source_key:      Key in the raw record (defaults to name).
        type_coerce:     Type or callable to convert the raw value.
        required:        Raise if missing and no default is set.
        default:         Static fallback value.
        default_factory: Callable producing a fresh default each time.
        validator:       Called with the final value; raise to reject.
        pre_process:     Transforms the raw value before coercion.
    """

    name: str
    source_key: str | None = None
    type_coerce: type | Callable[[Any], Any] | None = None
    required: bool = True
    default: Any = MISSING
    default_factory: Callable[[], Any] | None = None
    validator: Callable[[Any], None] | None = None
    pre_process: Callable[[Any], Any] | None = None

    def __post_init__(self) -> None:
        if self.source_key is None:
            self.source_key = self.name

    def get_value(self, record: dict[str, Any]) -> Any:
        raw = record.get(self.source_key)  # type: ignore[arg-type]
        if raw is None:
            return self._resolve_missing()
        return self._transform(raw)

    def _resolve_missing(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        if self.default is not MISSING:
            return self.default
        if not self.required:
            return None
        raise InjectionError(
            f"Required field '{self.name}' (source key: '{self.source_key}') "
            f"is absent in the record."
        )

    def _transform(self, value: Any) -> Any:
        if self.pre_process is not None:
            value = self.pre_process(value)

        if self.type_coerce is not None:
            already_correct = (
                isinstance(self.type_coerce, type)
                and isinstance(value, self.type_coerce)
            )
            if not already_correct:
                try:
                    value = self.type_coerce(value)
                except (ValueError, TypeError) as exc:
                    raise InjectionError(
                        f"Field '{self.name}': cannot coerce {value!r} "
                        f"using {self.type_coerce}: {exc}"
                    ) from exc

        if self.validator is not None:
            try:
                self.validator(value)
            except (ValueError, AssertionError) as exc:
                raise InjectionError(
                    f"Field '{self.name}' failed validation: {exc}"
                ) from exc

        return value
```

- [ ] **Step 4: Run to confirm all pass**

```bash
pytest tests/test_data_injector/test_descriptors.py -v
```

Expected: `17 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/data_injector/descriptors.py tests/test_data_injector/test_descriptors.py
git commit -m "feat(data_injector): add FieldDescriptor with coercion, defaults, and validation"
```

---

## Task 4: `Schema[T]`

**Files:**
- Create: `src/pyre/data_injector/schema.py`
- Create: `tests/test_data_injector/test_schema.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_data_injector/test_schema.py
from dataclasses import dataclass, field

import pytest

from pyre.data_injector.descriptors import FieldDescriptor
from pyre.data_injector.schema import Schema


@dataclass
class Simple:
    name: str
    value: float
    notes: str = "none"


@dataclass
class WithFactory:
    tags: list = field(default_factory=list)


class TestSchemaFromDataclass:
    def test_derives_fields_from_dataclass(self):
        schema = Schema.from_dataclass(Simple)
        names = [f.name for f in schema.fields]
        assert names == ["name", "value", "notes"]

    def test_required_fields_have_required_true(self):
        schema = Schema.from_dataclass(Simple)
        fd_name = next(f for f in schema.fields if f.name == "name")
        fd_value = next(f for f in schema.fields if f.name == "value")
        assert fd_name.required is True
        assert fd_value.required is True

    def test_fields_with_defaults_have_required_false(self):
        schema = Schema.from_dataclass(Simple)
        fd_notes = next(f for f in schema.fields if f.name == "notes")
        assert fd_notes.required is False
        assert fd_notes.default == "none"

    def test_fields_with_factory_have_required_false(self):
        schema = Schema.from_dataclass(WithFactory)
        fd_tags = next(f for f in schema.fields if f.name == "tags")
        assert fd_tags.required is False
        assert fd_tags.default_factory is list

    def test_override_replaces_auto_descriptor(self):
        override = FieldDescriptor(name="name", source_key="full_name", required=True)
        schema = Schema.from_dataclass(Simple, name=override)
        fd = next(f for f in schema.fields if f.name == "name")
        assert fd.source_key == "full_name"

    def test_non_dataclass_raises(self):
        with pytest.raises(TypeError, match="not a dataclass"):
            Schema.from_dataclass(dict)

    def test_target_class_stored(self):
        schema = Schema.from_dataclass(Simple)
        assert schema.target_class is Simple

    def test_default_nested_and_hooks_are_empty(self):
        schema = Schema.from_dataclass(Simple)
        assert schema.nested == {}
        assert schema.pre_hooks == []
        assert schema.post_hooks == []
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_data_injector/test_schema.py -v
```

Expected: `ImportError: cannot import name 'Schema'`

- [ ] **Step 3: Write `schema.py`**

```python
# src/pyre/data_injector/schema.py
from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from .descriptors import FieldDescriptor

T = TypeVar("T")


@dataclasses.dataclass
class Schema(Generic[T]):
    """Describes how a normalised dict maps onto target class T.

    Attributes:
        target_class: The class to construct.
        fields:       Ordered list of field descriptors.
        nested:       Maps attribute name -> Schema for nested objects.
        pre_hooks:    Transform the raw record before field extraction.
        post_hooks:   Transform the constructed instance before returning.
    """

    target_class: type[T]
    fields: list[FieldDescriptor]
    nested: dict[str, "Schema[Any]"] = dataclasses.field(default_factory=dict)
    pre_hooks: list[Callable[[dict[str, Any]], dict[str, Any]]] = dataclasses.field(
        default_factory=list
    )
    post_hooks: list[Callable[[T], T]] = dataclasses.field(default_factory=list)

    @classmethod
    def from_dataclass(
        cls, dc: type[T], **overrides: FieldDescriptor
    ) -> "Schema[T]":
        """Auto-derive a Schema from a dataclass's declared fields.

        Pass keyword arguments named after fields to supply custom
        FieldDescriptors that override the auto-derived ones.
        """
        if not dataclasses.is_dataclass(dc):
            raise TypeError(f"{dc!r} is not a dataclass")

        fields: list[FieldDescriptor] = []
        for f in dataclasses.fields(dc):  # type: ignore[arg-type]
            if f.name in overrides:
                fields.append(overrides[f.name])
                continue

            has_default = f.default is not dataclasses.MISSING
            has_factory = f.default_factory is not dataclasses.MISSING  # type: ignore[misc]

            fields.append(
                FieldDescriptor(
                    name=f.name,
                    required=not has_default and not has_factory,
                    default=f.default if has_default else dataclasses.MISSING,
                    default_factory=(
                        f.default_factory if has_factory else None  # type: ignore[misc]
                    ),
                )
            )
        return cls(target_class=dc, fields=fields)
```

- [ ] **Step 4: Run to confirm all pass**

```bash
pytest tests/test_data_injector/test_schema.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/data_injector/schema.py tests/test_data_injector/test_schema.py
git commit -m "feat(data_injector): add Schema with auto-derivation from dataclasses"
```

---

## Task 5: `Injector[T]` — flat records and error aggregation

**Files:**
- Create: `src/pyre/data_injector/injector.py`
- Create: `tests/test_data_injector/test_injector.py`

- [ ] **Step 1: Write the failing tests (flat injection)**

```python
# tests/test_data_injector/test_injector.py
from dataclasses import dataclass, field
from datetime import date

import pytest

from pyre.data_injector.descriptors import FieldDescriptor
from pyre.data_injector.exceptions import InjectionError
from pyre.data_injector.injector import Injector
from pyre.data_injector.schema import Schema


# ── shared fixtures ──────────────────────────────────────────────────────────

@dataclass
class Policy:
    policy_id: str
    premium: float
    inception_date: date
    notes: str = "none"


POLICY_SCHEMA = Schema(
    target_class=Policy,
    fields=[
        FieldDescriptor("policy_id"),
        FieldDescriptor("premium", type_coerce=float),
        FieldDescriptor("inception_date", type_coerce=date.fromisoformat),
        FieldDescriptor("notes", required=False, default="none"),
    ],
)


class TestInjectorFlat:
    def test_constructs_instance_from_record(self):
        record = {
            "policy_id": "POL-001",
            "premium": "5000.0",
            "inception_date": "2024-01-01",
        }
        result = Injector(POLICY_SCHEMA).inject(record)
        assert isinstance(result, Policy)
        assert result.policy_id == "POL-001"
        assert result.premium == pytest.approx(5000.0)
        assert result.inception_date == date(2024, 1, 1)
        assert result.notes == "none"

    def test_uses_provided_optional_value(self):
        record = {
            "policy_id": "POL-002",
            "premium": 1000.0,
            "inception_date": "2024-06-01",
            "notes": "renewal",
        }
        result = Injector(POLICY_SCHEMA).inject(record)
        assert result.notes == "renewal"

    def test_missing_required_field_raises(self):
        with pytest.raises(InjectionError, match="Required field 'policy_id'"):
            Injector(POLICY_SCHEMA).inject({"premium": 100.0, "inception_date": "2024-01-01"})


class TestInjectorPreHooks:
    def test_pre_hook_transforms_record_before_injection(self):
        def strip_whitespace(r: dict) -> dict:
            return {k: v.strip() if isinstance(v, str) else v for k, v in r.items()}

        schema = Schema(
            target_class=Policy,
            fields=POLICY_SCHEMA.fields,
            pre_hooks=[strip_whitespace],
        )
        record = {
            "policy_id": "  POL-003  ",
            "premium": 200.0,
            "inception_date": "2024-03-01",
        }
        result = Injector(schema).inject(record)
        assert result.policy_id == "POL-003"


class TestInjectorPostHooks:
    def test_post_hook_transforms_instance(self):
        def uppercase_id(p: Policy) -> Policy:
            p.policy_id = p.policy_id.upper()
            return p

        schema = Schema(
            target_class=Policy,
            fields=POLICY_SCHEMA.fields,
            post_hooks=[uppercase_id],
        )
        result = Injector(schema).inject({
            "policy_id": "pol-004",
            "premium": 300.0,
            "inception_date": "2024-04-01",
        })
        assert result.policy_id == "POL-004"


class TestInjectMany:
    def test_injects_list_of_records(self):
        records = [
            {"policy_id": f"POL-{i:03d}", "premium": float(i * 100), "inception_date": "2024-01-01"}
            for i in range(1, 4)
        ]
        results = Injector(POLICY_SCHEMA).inject_many(records)
        assert len(results) == 3
        assert results[0].policy_id == "POL-001"

    def test_aggregates_errors_across_all_records(self):
        records = [
            {"policy_id": "POL-001", "premium": 100.0, "inception_date": "2024-01-01"},
            {"premium": 200.0, "inception_date": "2024-01-01"},   # missing policy_id
            {"policy_id": "POL-003", "inception_date": "2024-01-01"},  # missing premium
        ]
        with pytest.raises(InjectionError) as exc_info:
            Injector(POLICY_SCHEMA).inject_many(records)
        msg = str(exc_info.value)
        assert "2 of 3" in msg
        assert "Record 1" in msg
        assert "Record 2" in msg


class TestInjectorNested:
    def test_injects_nested_dataclass(self):
        @dataclass
        class Address:
            city: str
            postcode: str

        @dataclass
        class Holder:
            name: str
            address: Address

        address_schema = Schema(
            target_class=Address,
            fields=[FieldDescriptor("city"), FieldDescriptor("postcode")],
        )
        holder_schema = Schema(
            target_class=Holder,
            fields=[FieldDescriptor("name"), FieldDescriptor("address")],
            nested={"address": address_schema},
        )
        record = {"name": "Alice", "address": {"city": "London", "postcode": "EC1"}}
        result = Injector(holder_schema).inject(record)
        assert isinstance(result.address, Address)
        assert result.address.city == "London"

    def test_non_dict_nested_field_raises(self):
        @dataclass
        class Address:
            city: str

        @dataclass
        class Holder:
            name: str
            address: Address

        address_schema = Schema(target_class=Address, fields=[FieldDescriptor("city")])
        holder_schema = Schema(
            target_class=Holder,
            fields=[FieldDescriptor("name"), FieldDescriptor("address")],
            nested={"address": address_schema},
        )
        with pytest.raises(InjectionError, match="expected a dict"):
            Injector(holder_schema).inject({"name": "Bob", "address": "not-a-dict"})
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_data_injector/test_injector.py -v
```

Expected: `ImportError: cannot import name 'Injector'`

- [ ] **Step 3: Write `injector.py`**

```python
# src/pyre/data_injector/injector.py
from __future__ import annotations

from typing import Any, Generic, TypeVar

from .exceptions import InjectionError
from .schema import Schema

T = TypeVar("T")


class Injector(Generic[T]):
    """Walks a Schema and constructs instances of T from normalised records."""

    def __init__(self, schema: Schema[T]) -> None:
        self._schema = schema

    def inject(self, record: dict[str, Any]) -> T:
        for hook in self._schema.pre_hooks:
            record = hook(record)

        kwargs: dict[str, Any] = {}
        for fd in self._schema.fields:
            if fd.name in self._schema.nested:
                kwargs[fd.name] = self._inject_nested(fd, record)
            else:
                kwargs[fd.name] = fd.get_value(record)

        try:
            instance: T = self._schema.target_class(**kwargs)
        except TypeError as exc:
            raise InjectionError(
                f"Could not construct {self._schema.target_class.__name__}: {exc}"
            ) from exc

        for hook in self._schema.post_hooks:
            instance = hook(instance)

        return instance

    def inject_many(self, records: list[dict[str, Any]]) -> list[T]:
        results: list[T] = []
        errors: list[str] = []
        for i, record in enumerate(records):
            try:
                results.append(self.inject(record))
            except InjectionError as exc:
                errors.append(f"  Record {i}: {exc}")
        if errors:
            raise InjectionError(
                f"Injection failed for {len(errors)} of {len(records)} record(s):\n"
                + "\n".join(errors)
            )
        return results

    def _inject_nested(self, fd: Any, record: dict[str, Any]) -> Any:
        nested_schema = self._schema.nested[fd.name]
        sub = record.get(fd.source_key or fd.name)
        if sub is None:
            return fd._resolve_missing()
        if not isinstance(sub, dict):
            raise InjectionError(
                f"Field '{fd.name}' expected a dict for nested injection, "
                f"got {type(sub).__name__}"
            )
        return Injector(nested_schema).inject(sub)
```

- [ ] **Step 4: Run to confirm all pass**

```bash
pytest tests/test_data_injector/test_injector.py -v
```

Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/data_injector/injector.py tests/test_data_injector/test_injector.py
git commit -m "feat(data_injector): add Injector with flat, nested, hooks, and error aggregation"
```

---

## Task 6: Source adapters

**Files:**
- Create: `src/pyre/data_injector/adapters/base.py`
- Create: `src/pyre/data_injector/adapters/dict_adapter.py`
- Create: `src/pyre/data_injector/adapters/json_adapter.py`
- Create: `src/pyre/data_injector/adapters/csv_adapter.py`
- Create: `src/pyre/data_injector/adapters/yaml_adapter.py`
- Create: `src/pyre/data_injector/adapters/excel_adapter.py`
- Create: `tests/test_data_injector/test_adapters.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_data_injector/test_adapters.py
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

from pyre.data_injector.adapters.base import SourceAdapter
from pyre.data_injector.adapters.csv_adapter import CSVAdapter
from pyre.data_injector.adapters.dict_adapter import DictAdapter
from pyre.data_injector.adapters.json_adapter import JSONAdapter


# ── DictAdapter ──────────────────────────────────────────────────────────────

class TestDictAdapter:
    def test_accepts_plain_dict(self):
        records = DictAdapter().load({"a": 1, "b": 2})
        assert records == [{"a": 1, "b": 2}]

    def test_accepts_list_of_dicts(self):
        records = DictAdapter().load([{"x": 1}, {"x": 2}])
        assert records == [{"x": 1}, {"x": 2}]

    def test_accepts_dataclass_instance(self):
        @dataclass
        class Point:
            x: int
            y: int

        records = DictAdapter().load(Point(x=3, y=4))
        assert records == [{"x": 3, "y": 4}]

    def test_accepts_list_of_dataclasses(self):
        @dataclass
        class Point:
            x: int

        records = DictAdapter().load([Point(x=1), Point(x=2)])
        assert records == [{"x": 1}, {"x": 2}]

    def test_accepts_plain_object_with_dict(self):
        class Obj:
            def __init__(self) -> None:
                self.name = "test"

        records = DictAdapter().load(Obj())
        assert records == [{"name": "test"}]

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError, match="cannot convert"):
            DictAdapter().load(42)


# ── JSONAdapter ──────────────────────────────────────────────────────────────

class TestJSONAdapter:
    def test_loads_list_from_file(self, tmp_path: Path):
        data = [{"id": "A"}, {"id": "B"}]
        p = tmp_path / "data.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        assert JSONAdapter().load(p) == data

    def test_loads_single_dict_wrapped_in_list(self, tmp_path: Path):
        p = tmp_path / "single.json"
        p.write_text(json.dumps({"id": "X"}), encoding="utf-8")
        assert JSONAdapter().load(p) == [{"id": "X"}]

    def test_accepts_raw_dict(self):
        assert JSONAdapter().load({"k": "v"}) == [{"k": "v"}]

    def test_accepts_raw_list(self):
        assert JSONAdapter().load([{"k": "v"}]) == [{"k": "v"}]

    def test_invalid_root_type_raises(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text('"just a string"', encoding="utf-8")
        with pytest.raises(ValueError, match="expected dict or list"):
            JSONAdapter().load(p)


# ── CSVAdapter ───────────────────────────────────────────────────────────────

class TestCSVAdapter:
    def test_loads_rows_as_list_of_dicts(self, tmp_path: Path):
        csv_text = textwrap.dedent("""\
            id,name,value
            1,Alice,100
            2,Bob,200
        """)
        p = tmp_path / "data.csv"
        p.write_text(csv_text, encoding="utf-8")
        records = CSVAdapter().load(p)
        assert len(records) == 2
        assert records[0] == {"id": "1", "name": "Alice", "value": "100"}
        assert records[1] == {"id": "2", "name": "Bob", "value": "200"}

    def test_custom_delimiter(self, tmp_path: Path):
        csv_text = "id;name\n1;Alice\n"
        p = tmp_path / "data.csv"
        p.write_text(csv_text, encoding="utf-8")
        records = CSVAdapter(delimiter=";").load(p)
        assert records[0] == {"id": "1", "name": "Alice"}

    def test_empty_file_returns_empty_list(self, tmp_path: Path):
        p = tmp_path / "empty.csv"
        p.write_text("", encoding="utf-8")
        assert CSVAdapter().load(p) == []


# ── Protocol check ────────────────────────────────────────────────────────────

class TestSourceAdapterProtocol:
    def test_dict_adapter_satisfies_protocol(self):
        assert isinstance(DictAdapter(), SourceAdapter)

    def test_json_adapter_satisfies_protocol(self):
        assert isinstance(JSONAdapter(), SourceAdapter)

    def test_csv_adapter_satisfies_protocol(self):
        assert isinstance(CSVAdapter(), SourceAdapter)
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_data_injector/test_adapters.py -v
```

Expected: `ImportError` for missing adapter modules.

- [ ] **Step 3: Write `adapters/base.py`**

```python
# src/pyre/data_injector/adapters/base.py
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceAdapter(Protocol):
    """All adapters satisfy this protocol — no inheritance required."""

    def load(self, source: Any) -> list[dict[str, Any]]:
        """Return a normalised list of records from the source."""
        ...
```

- [ ] **Step 4: Write `adapters/dict_adapter.py`**

```python
# src/pyre/data_injector/adapters/dict_adapter.py
from __future__ import annotations

import dataclasses
from typing import Any


class DictAdapter:
    """Accepts dicts, lists, dataclass instances, or objects with __dict__."""

    def load(self, source: Any) -> list[dict[str, Any]]:
        if isinstance(source, list):
            return [self._to_dict(item) for item in source]
        return [self._to_dict(source)]

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, Any]:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "__dict__"):
            return vars(obj)
        raise TypeError(f"DictAdapter: cannot convert {type(obj).__name__} to dict")
```

- [ ] **Step 5: Write `adapters/json_adapter.py`**

```python
# src/pyre/data_injector/adapters/json_adapter.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JSONAdapter:
    def load(self, source: str | Path | dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
        if isinstance(source, (str, Path)):
            raw = json.loads(Path(source).read_text(encoding="utf-8"))
        else:
            raw = source
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return [raw]
        raise ValueError(
            f"JSONAdapter: expected dict or list at root, got {type(raw).__name__}"
        )
```

- [ ] **Step 6: Write `adapters/csv_adapter.py`**

```python
# src/pyre/data_injector/adapters/csv_adapter.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


class CSVAdapter:
    def __init__(self, delimiter: str = ",", encoding: str = "utf-8") -> None:
        self._delimiter = delimiter
        self._encoding = encoding

    def load(self, source: str | Path) -> list[dict[str, Any]]:
        path = Path(source)
        with path.open(newline="", encoding=self._encoding) as fh:
            reader = csv.DictReader(fh, delimiter=self._delimiter)
            if reader.fieldnames is None:
                return []
            return [dict(row) for row in reader]
```

- [ ] **Step 7: Write `adapters/yaml_adapter.py`**

```python
# src/pyre/data_injector/adapters/yaml_adapter.py
from __future__ import annotations

from pathlib import Path
from typing import Any


class YAMLAdapter:
    def load(self, source: str | Path) -> list[dict[str, Any]]:
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "PyYAML is required for YAML support: pip install pyyaml"
            ) from exc
        raw = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return [raw]
        raise ValueError(f"YAMLAdapter: unexpected root type {type(raw).__name__}")
```

- [ ] **Step 8: Write `adapters/excel_adapter.py`**

```python
# src/pyre/data_injector/adapters/excel_adapter.py
from __future__ import annotations

from pathlib import Path
from typing import Any


class ExcelAdapter:
    def __init__(self, sheet_name: str | int = 0) -> None:
        self._sheet_name = sheet_name

    def load(self, source: str | Path) -> list[dict[str, Any]]:
        try:
            import openpyxl
        except ImportError as exc:
            raise ImportError(
                "openpyxl is required for Excel support: pip install openpyxl"
            ) from exc
        wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
        ws = (
            wb.worksheets[self._sheet_name]
            if isinstance(self._sheet_name, int)
            else wb[self._sheet_name]
        )
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [
            str(h) if h is not None else f"col_{i}"
            for i, h in enumerate(rows[0])
        ]
        return [dict(zip(headers, row)) for row in rows[1:]]
```

- [ ] **Step 9: Run tests to confirm all pass**

```bash
pytest tests/test_data_injector/test_adapters.py -v
```

Expected: `17 passed`

- [ ] **Step 10: Commit**

```bash
git add src/pyre/data_injector/adapters/ tests/test_data_injector/test_adapters.py
git commit -m "feat(data_injector): add all five source adapters (dict, JSON, CSV, YAML, Excel)"
```

---

## Task 7: `AdapterRegistry`

**Files:**
- Create: `src/pyre/data_injector/registry.py`
- Create: `tests/test_data_injector/test_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_data_injector/test_registry.py
from typing import Any

import pytest

from pyre.data_injector.registry import AdapterRegistry


class TestAdapterRegistry:
    def setup_method(self) -> None:
        # Clear any registrations from previous tests
        AdapterRegistry._adapters.clear()

    def test_register_and_retrieve(self):
        @AdapterRegistry.register("custom")
        class CustomAdapter:
            def load(self, source: Any) -> list[dict[str, Any]]:
                return [{"from": "custom"}]

        cls = AdapterRegistry.get("custom")
        assert cls is CustomAdapter

    def test_get_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="No adapter registered for 'parquet'"):
            AdapterRegistry.get("parquet")

    def test_available_lists_registered_names(self):
        @AdapterRegistry.register("alpha")
        class A:
            def load(self, source: Any) -> list[dict[str, Any]]: return []

        @AdapterRegistry.register("beta")
        class B:
            def load(self, source: Any) -> list[dict[str, Any]]: return []

        assert AdapterRegistry.available() == ["alpha", "beta"]

    def test_register_decorator_returns_class_unchanged(self):
        @AdapterRegistry.register("passthrough")
        class PT:
            def load(self, source: Any) -> list[dict[str, Any]]: return []

        assert PT.__name__ == "PT"
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_data_injector/test_registry.py -v
```

Expected: `ImportError: cannot import name 'AdapterRegistry'`

- [ ] **Step 3: Write `registry.py`**

```python
# src/pyre/data_injector/registry.py
from __future__ import annotations

from collections.abc import Callable


class AdapterRegistry:
    """Class-level registry for third-party and user-defined adapters.

    Usage::

        @AdapterRegistry.register("parquet")
        class ParquetAdapter:
            def load(self, source): ...

        cls = AdapterRegistry.get("parquet")
        records = cls().load("data.parquet")
    """

    _adapters: dict[str, type] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[type], type]:
        def decorator(adapter_cls: type) -> type:
            cls._adapters[name] = adapter_cls
            return adapter_cls
        return decorator

    @classmethod
    def get(cls, name: str) -> type:
        if name not in cls._adapters:
            available = ", ".join(sorted(cls._adapters)) or "(none)"
            raise KeyError(
                f"No adapter registered for '{name}'. Available: {available}"
            )
        return cls._adapters[name]

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._adapters)
```

- [ ] **Step 4: Run to confirm all pass**

```bash
pytest tests/test_data_injector/test_registry.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/data_injector/registry.py tests/test_data_injector/test_registry.py
git commit -m "feat(data_injector): add AdapterRegistry for plugin-style adapter extension"
```

---

## Task 8: `Loader[T]` facade + integration tests

**Files:**
- Create: `src/pyre/data_injector/loader.py`
- Create: `tests/test_data_injector/test_loader.py`

- [ ] **Step 1: Write the failing integration tests**

```python
# tests/test_data_injector/test_loader.py
import json
import textwrap
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pytest

from pyre.data_injector.descriptors import FieldDescriptor
from pyre.data_injector.exceptions import InjectionError
from pyre.data_injector.loader import Loader
from pyre.data_injector.schema import Schema
from pyre.data_injector.utils import unflatten


# ── shared models ────────────────────────────────────────────────────────────

@dataclass
class Address:
    street: str
    city: str
    postcode: str
    country: str = "GB"


@dataclass
class PolicyHolder:
    policy_id: str
    holder_name: str
    inception_date: date
    premium: float
    address: Address
    tags: list = field(default_factory=list)
    notes: str | None = None


ADDRESS_SCHEMA = Schema(
    target_class=Address,
    fields=[
        FieldDescriptor("street"),
        FieldDescriptor("city"),
        FieldDescriptor("postcode"),
        FieldDescriptor("country", required=False, default="GB"),
    ],
)

HOLDER_SCHEMA = Schema(
    target_class=PolicyHolder,
    fields=[
        FieldDescriptor("policy_id"),
        FieldDescriptor("holder_name"),
        FieldDescriptor("inception_date", type_coerce=date.fromisoformat),
        FieldDescriptor("premium", type_coerce=float),
        FieldDescriptor("address"),
        FieldDescriptor("tags", required=False, default_factory=list),
        FieldDescriptor("notes", required=False),
    ],
    nested={"address": ADDRESS_SCHEMA},
)


# ── from_dict ────────────────────────────────────────────────────────────────

class TestLoaderFromDict:
    def test_single_dict(self):
        raw = {
            "policy_id": "POL-001",
            "holder_name": "Acme Ltd",
            "inception_date": "2024-01-15",
            "premium": 12500.50,
            "address": {"street": "10 Finsbury Sq", "city": "London", "postcode": "EC2A"},
        }
        loader: Loader[PolicyHolder] = Loader(HOLDER_SCHEMA)
        result = loader.from_dict(raw)
        assert len(result) == 1
        assert result[0].policy_id == "POL-001"
        assert isinstance(result[0].address, Address)
        assert result[0].address.city == "London"

    def test_from_one(self):
        raw = {
            "policy_id": "POL-002",
            "holder_name": "Beta Re",
            "inception_date": "2024-03-01",
            "premium": 8000.0,
            "address": {"street": "5 King St", "city": "Manchester", "postcode": "M2"},
        }
        loader: Loader[PolicyHolder] = Loader(HOLDER_SCHEMA)
        result = loader.from_one(raw)
        assert isinstance(result, PolicyHolder)
        assert result.premium == pytest.approx(8000.0)


# ── from_json ────────────────────────────────────────────────────────────────

class TestLoaderFromJSON:
    def test_loads_list_from_json_file(self, tmp_path: Path):
        data = [
            {
                "policy_id": "POL-003",
                "holder_name": "Gamma PLC",
                "inception_date": "2024-06-01",
                "premium": "22000",
                "address": {"street": "1 Queen Rd", "city": "Edinburgh", "postcode": "EH1"},
            }
        ]
        p = tmp_path / "policies.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        loader: Loader[PolicyHolder] = Loader(HOLDER_SCHEMA)
        results = loader.from_json(p)
        assert len(results) == 1
        assert results[0].premium == pytest.approx(22000.0)
        assert results[0].address.country == "GB"  # default applied


# ── from_csv ─────────────────────────────────────────────────────────────────

class TestLoaderFromCSV:
    def test_loads_flat_csv_with_unflatten_pre_hook(self, tmp_path: Path):
        csv_text = textwrap.dedent("""\
            policy_id,holder_name,inception_date,premium,address.street,address.city,address.postcode
            POL-004,Delta Re,2024-09-01,45000,30 Lime St,London,EC3M
        """)
        p = tmp_path / "policies.csv"
        p.write_text(csv_text, encoding="utf-8")

        schema_with_unflatten = Schema(
            target_class=HOLDER_SCHEMA.target_class,
            fields=HOLDER_SCHEMA.fields,
            nested=HOLDER_SCHEMA.nested,
            pre_hooks=[unflatten],
        )
        loader: Loader[PolicyHolder] = Loader(schema_with_unflatten)
        results = loader.from_csv(p)
        assert len(results) == 1
        assert results[0].policy_id == "POL-004"
        assert results[0].address.city == "London"

    def test_all_string_values_are_coerced(self, tmp_path: Path):
        csv_text = "policy_id,holder_name,inception_date,premium,address.street,address.city,address.postcode\nPOL-005,Epsilon,2024-10-01,9999,1 A St,York,YO1\n"
        p = tmp_path / "p.csv"
        p.write_text(csv_text, encoding="utf-8")
        schema_with_unflatten = Schema(
            target_class=HOLDER_SCHEMA.target_class,
            fields=HOLDER_SCHEMA.fields,
            nested=HOLDER_SCHEMA.nested,
            pre_hooks=[unflatten],
        )
        result = Loader(schema_with_unflatten).from_csv(p)[0]
        assert result.premium == pytest.approx(9999.0)
        assert result.inception_date == date(2024, 10, 1)


# ── Loader.for_class ──────────────────────────────────────────────────────────

class TestLoaderForClass:
    def test_auto_derives_schema_from_dataclass(self):
        @dataclass
        class RateChange:
            year: int
            factor: float
            source: str = "manual"

        loader = Loader.for_class(RateChange)
        records = [{"year": 2024, "factor": 1.05}, {"year": 2023, "factor": 0.97}]
        results = loader.from_dict(records)
        assert len(results) == 2
        assert results[0].source == "manual"
        assert results[1].factor == pytest.approx(0.97)
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_data_injector/test_loader.py -v
```

Expected: `ImportError: cannot import name 'Loader'`

- [ ] **Step 3: Write `loader.py`**

```python
# src/pyre/data_injector/loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Generic, TypeVar

from .adapters.csv_adapter import CSVAdapter
from .adapters.dict_adapter import DictAdapter
from .adapters.excel_adapter import ExcelAdapter
from .adapters.json_adapter import JSONAdapter
from .adapters.yaml_adapter import YAMLAdapter
from .descriptors import FieldDescriptor
from .injector import Injector
from .schema import Schema

T = TypeVar("T")


class Loader(Generic[T]):
    """High-level facade: picks the right adapter and runs the injector.

    Typical usage::

        loader = Loader(my_schema)
        instances = loader.from_json("data.json")

    Or for simple dataclasses without nesting::

        loader = Loader.for_class(MyClass)
        instances = loader.from_csv("data.csv")
    """

    def __init__(self, schema: Schema[T]) -> None:
        self._schema = schema
        self._injector = Injector(schema)

    @classmethod
    def for_class(cls, target: type[T], **overrides: FieldDescriptor) -> "Loader[T]":
        """Auto-derive schema from a dataclass and return a ready Loader."""
        return cls(Schema.from_dataclass(target, **overrides))

    # ── source methods ────────────────────────────────────────────────────────

    def from_json(self, source: str | Path | dict | list) -> list[T]:
        return self._injector.inject_many(JSONAdapter().load(source))

    def from_csv(self, source: str | Path, **csv_kwargs: Any) -> list[T]:
        return self._injector.inject_many(CSVAdapter(**csv_kwargs).load(source))

    def from_yaml(self, source: str | Path) -> list[T]:
        return self._injector.inject_many(YAMLAdapter().load(source))

    def from_excel(self, source: str | Path, sheet_name: str | int = 0) -> list[T]:
        return self._injector.inject_many(ExcelAdapter(sheet_name).load(source))

    def from_dict(self, source: Any) -> list[T]:
        return self._injector.inject_many(DictAdapter().load(source))

    def from_one(self, record: dict[str, Any]) -> T:
        return self._injector.inject(record)
```

- [ ] **Step 4: Run to confirm all pass**

```bash
pytest tests/test_data_injector/test_loader.py -v
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pyre/data_injector/loader.py tests/test_data_injector/test_loader.py
git commit -m "feat(data_injector): add Loader facade with JSON, CSV, YAML, Excel, dict support"
```

---

## Task 9: Public `__init__.py` and full suite verification

**Files:**
- Modify: `src/pyre/data_injector/__init__.py`

- [ ] **Step 1: Write the failing import test**

```python
# Add to tests/test_data_injector/test_loader.py (bottom of file)

class TestPublicAPI:
    def test_top_level_imports(self):
        from pyre.data_injector import (
            FieldDescriptor,
            InjectionError,
            Injector,
            Loader,
            Schema,
            unflatten,
        )
        assert FieldDescriptor is not None
        assert InjectionError is not None
        assert Injector is not None
        assert Loader is not None
        assert Schema is not None
        assert unflatten is not None
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_data_injector/test_loader.py::TestPublicAPI -v
```

Expected: `ImportError: cannot import name 'FieldDescriptor' from 'pyre.data_injector'`

- [ ] **Step 3: Write `__init__.py`**

```python
# src/pyre/data_injector/__init__.py
from .descriptors import FieldDescriptor as FieldDescriptor
from .exceptions import InjectionError as InjectionError
from .injector import Injector as Injector
from .loader import Loader as Loader
from .registry import AdapterRegistry as AdapterRegistry
from .schema import Schema as Schema
from .utils import parse_bool as parse_bool
from .utils import parse_list as parse_list
from .utils import unflatten as unflatten
```

- [ ] **Step 4: Run the full test suite**

```bash
pytest tests/test_data_injector/ -v --tb=short
```

Expected: All tests pass. Tally should be approximately 60 passed.

- [ ] **Step 5: Run the full project suite to check for regressions**

```bash
pytest --tb=short -q
```

Expected: All original tests pass alongside the new tests.

- [ ] **Step 6: Check ruff and mypy**

```bash
ruff check src/pyre/data_injector/ tests/test_data_injector/
mypy src/pyre/data_injector/
```

Expected: 0 errors from both.

- [ ] **Step 7: Commit**

```bash
git add src/pyre/data_injector/__init__.py tests/test_data_injector/test_loader.py
git commit -m "feat(data_injector): expose public API via __init__.py; all tests green"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Base injector/loader abstraction → `Injector`, `Loader`
- [x] Automatic key/field mapping → `FieldDescriptor.source_key`
- [x] Optional fields, defaults, type coercion → `FieldDescriptor`
- [x] Nested objects → `Schema.nested` + `Injector._inject_nested`
- [x] Error handling with clear messages → `InjectionError` + `inject_many` aggregation
- [x] JSON, CSV, YAML, Excel, dict adapters → Tasks 6
- [x] Intermediate representation (`list[dict]`) → adapter Protocol return type
- [x] Plugin-style architecture → `AdapterRegistry`
- [x] Configurable field mappings → `source_key` on `FieldDescriptor`
- [x] Pre/post hooks → `Schema.pre_hooks`, `Schema.post_hooks`
- [x] Example target classes with nesting → `PolicyHolder` + `Address` in tests
- [x] `unflatten` for flat CSV → Task 2 + Task 8 integration test

**Type consistency:**
- `Schema.nested: dict[str, Schema[Any]]` used consistently in Tasks 4, 5, 8
- `Injector._inject_nested` receives `FieldDescriptor` — typed as `Any` internally to avoid circular import; acceptable
- `Loader.for_class` uses `Schema.from_dataclass` which is defined in Task 4
- `CSVAdapter` returns `list[dict[str, Any]]` — all string values; coercion handled by `FieldDescriptor` in Task 3

**No placeholders:** None found.
