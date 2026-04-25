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
