# tests/test_data_injector/test_domain_schemas/test_exposure_schemas.py
from __future__ import annotations

import sqlite3
import textwrap
from datetime import date
from pathlib import Path

import pytest

from pyre.data_injector.domain_schemas.exposure_schemas import (
    exposure_meta_schema,
    exposure_schema,
    exposure_values_schema,
    exposures_db_loader,
    exposures_loader,
)
from pyre.exposures.exposures import Exposure, ExposureMetaData, ExposureValues


class TestExposureMetaSchema:
    def test_target_class(self) -> None:
        assert exposure_meta_schema.target_class is ExposureMetaData

    def test_required_fields_present(self) -> None:
        names = [f.name for f in exposure_meta_schema.fields]
        for required in ("exposure_id", "exposure_name", "exposure_period_start",
                         "exposure_period_end", "currency"):
            assert required in names

    def test_dates_coerced_from_iso_strings(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {
            "exposure_id": "E1", "exposure_name": "Test",
            "exposure_period_start": "2024-01-01",
            "exposure_period_end": "2024-12-31", "currency": "GBP",
        }
        meta = Injector(exposure_meta_schema).inject(record)
        assert meta.exposure_period_start == date(2024, 1, 1)
        assert meta.exposure_period_end == date(2024, 12, 31)

    def test_optional_fields_default(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {
            "exposure_id": "E2", "exposure_name": "Test2",
            "exposure_period_start": "2024-01-01",
            "exposure_period_end": "2024-12-31", "currency": "USD",
        }
        meta = Injector(exposure_meta_schema).inject(record)
        assert meta.aggregate is False
        assert meta.line_of_business is None


class TestExposureValuesSchema:
    def test_target_class(self) -> None:
        assert exposure_values_schema.target_class is ExposureValues

    def test_floats_coerced_from_strings(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {"exposure_value": "100000", "attachment_point": "5000", "limit": "50000"}
        values = Injector(exposure_values_schema).inject(record)
        assert values.exposure_value == pytest.approx(100000.0)
        assert values.limit == pytest.approx(50000.0)


class TestExposureSchema:
    def test_target_class(self) -> None:
        assert exposure_schema.target_class is Exposure

    def test_nested_keys_match_constructor_args(self) -> None:
        assert "exposure_meta" in exposure_schema.nested
        assert "exposure_values" in exposure_schema.nested

    def test_unflatten_in_pre_hooks(self) -> None:
        from pyre.data_injector.utils import unflatten
        assert unflatten in exposure_schema.pre_hooks

    def test_injects_flat_record(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {
            "exposure_meta.exposure_id": "E3",
            "exposure_meta.exposure_name": "Flat Test",
            "exposure_meta.exposure_period_start": "2024-01-01",
            "exposure_meta.exposure_period_end": "2024-12-31",
            "exposure_meta.currency": "GBP",
            "exposure_values.exposure_value": "200000",
            "exposure_values.attachment_point": "10000",
            "exposure_values.limit": "100000",
        }
        exposure = Injector(exposure_schema).inject(record)
        assert isinstance(exposure, Exposure)
        assert isinstance(exposure.exposure_meta, ExposureMetaData)
        assert exposure.exposure_meta.exposure_id == "E3"
        assert exposure.exposure_values.limit == pytest.approx(100000.0)


class TestExposuresLoader:
    def test_loads_from_csv(self, tmp_path: Path) -> None:
        csv_text = (
            "exposure_meta.exposure_id,exposure_meta.exposure_name,"
            "exposure_meta.exposure_period_start,exposure_meta.exposure_period_end,"
            "exposure_meta.currency,exposure_values.exposure_value,"
            "exposure_values.attachment_point,exposure_values.limit\n"
            "E4,CSV Exposure,2024-01-01,2024-12-31,GBP,500000,25000,250000"
        )
        p = tmp_path / "exposures.csv"
        p.write_text(csv_text, encoding="utf-8")
        loader = exposures_loader()
        results = loader.from_csv(p)
        assert len(results) == 1
        assert results[0].exposure_meta.exposure_id == "E4"
        assert results[0].exposure_values.exposure_value == pytest.approx(500000.0)

    def test_loads_from_sqlite(self, tmp_path: Path) -> None:
        db_path = tmp_path / "exposures.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE exposures ("
            "exposure_meta_exposure_id TEXT, exposure_meta_exposure_name TEXT,"
            "exposure_meta_exposure_period_start TEXT, exposure_meta_exposure_period_end TEXT,"
            "exposure_meta_currency TEXT, exposure_values_exposure_value REAL,"
            "exposure_values_attachment_point REAL, exposure_values_limit REAL)"
        )
        conn.execute(
            "INSERT INTO exposures VALUES (?,?,?,?,?,?,?,?)",
            ("E5", "DB Exposure", "2024-01-01", "2024-12-31", "USD", 1000000.0, 50000.0, 500000.0),
        )
        conn.commit()
        conn.close()
        loader = exposures_db_loader()
        results = loader.from_db(f"sqlite:///{db_path}", "SELECT * FROM exposures")
        assert len(results) == 1
        assert results[0].exposure_meta.exposure_id == "E5"
        assert results[0].exposure_values.limit == pytest.approx(500000.0)
