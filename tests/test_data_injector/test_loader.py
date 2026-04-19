# tests/test_data_injector/test_loader.py
import json
import textwrap
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pytest

from pyre.data_injector.descriptors import FieldDescriptor
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
