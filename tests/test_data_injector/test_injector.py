# tests/test_data_injector/test_injector.py
from dataclasses import dataclass
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
        result = Injector(schema).inject(
            {
                "policy_id": "pol-004",
                "premium": 300.0,
                "inception_date": "2024-04-01",
            }
        )
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
            {"premium": 200.0, "inception_date": "2024-01-01"},  # missing policy_id
            {
                "policy_id": "POL-003",
                "inception_date": "2024-01-01",
            },  # missing premium — wait, premium has type_coerce=float but no required=False. Actually premium IS required so this should fail on missing premium? No — premium is required=True but "premium" key is absent from this record, so it will raise on missing. BUT wait — premium has type_coerce=float but the record has no "premium" key, so get_value returns _resolve_missing which raises InjectionError.
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
