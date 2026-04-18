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
