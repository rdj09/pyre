# tests/test_app/test_storage_service.py
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from app.db.database import init_db
from app.services.domain_service import DomainService
from app.services.storage_service import StorageService
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, ClaimsMetaData
from pyre.enums import ClaimYearType, ExposureBasis
from pyre.exposures.exposures import Exposure, ExposureMetaData, ExposureValues


def _make_exposure(eid: str = "E-001", value: float = 50000.0) -> Exposure:
    return Exposure(
        exposure_meta=ExposureMetaData(
            exposure_id=eid,
            exposure_name="Test Portfolio",
            exposure_period_start=date(2024, 1, 1),
            exposure_period_end=date(2024, 12, 31),
            currency="GBP",
            aggregate=False,
            line_of_business="Property",
            exposure_type=ExposureBasis.WRITTEN,
        ),
        exposure_values=ExposureValues(
            exposure_value=value,
            attachment_point=2000.0,
            limit=3000.0,
        ),
    )


def _make_claim(cid: str = "CL-001") -> Claim:
    return Claim(
        claims_meta_data=ClaimsMetaData(
            claim_id=cid,
            currency="GBP",
            contract_limit=15000.0,
            contract_deductible=0.0,
            claim_in_xs_of_deductible=False,
            claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
            loss_date=date(2022, 6, 1),
            policy_inception_date=date(2022, 1, 1),
            report_date=date(2022, 7, 1),
            line_of_business="Property",
            status="Open",
        ),
        claims_development_history=ClaimDevelopmentHistory(
            development_months=[12, 24],
            cumulative_dev_paid=[5000.0, 9000.0],
            cumulative_dev_incurred=[7000.0, 11000.0],
        ),
    )


class TestInitDb:
    def test_creates_exposures_table(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        init_db(db)
        conn = sqlite3.connect(db)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='exposures'"
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_creates_claims_table(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        init_db(db)
        conn = sqlite3.connect(db)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='claims'"
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_idempotent(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        init_db(db)
        init_db(db)  # must not raise

    def test_exposures_pk_is_exposure_id(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        init_db(db)
        conn = sqlite3.connect(db)
        cur = conn.execute("PRAGMA table_info(exposures)")
        pk_cols = [row[1] for row in cur.fetchall() if row[5] == 1]
        conn.close()
        assert pk_cols == ["exposure_meta_exposure_id"]

    def test_claims_pk_is_claim_id(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        init_db(db)
        conn = sqlite3.connect(db)
        cur = conn.execute("PRAGMA table_info(claims)")
        pk_cols = [row[1] for row in cur.fetchall() if row[5] == 1]
        conn.close()
        assert pk_cols == ["claims_meta_data_claim_id"]


class TestStorageServiceSaveExposures:
    def test_saves_single_exposure(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_exposures([_make_exposure()], db)
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT exposure_meta_exposure_id FROM exposures").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "E-001"

    def test_saves_multiple_exposures(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_exposures([_make_exposure("E-001"), _make_exposure("E-002")], db)
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM exposures").fetchone()[0]
        conn.close()
        assert count == 2

    def test_upsert_replaces_existing(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        svc = StorageService()
        svc.save_exposures([_make_exposure("E-001", value=50000.0)], db)
        svc.save_exposures([_make_exposure("E-001", value=99999.0)], db)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT COUNT(*), exposure_values_exposure_value FROM exposures"
        ).fetchone()
        conn.close()
        assert row[0] == 1
        assert row[1] == pytest.approx(99999.0)

    def test_bool_serialized_as_int(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        e = Exposure(
            exposure_meta=ExposureMetaData(
                exposure_id="E-AGG",
                exposure_name="Agg",
                exposure_period_start=date(2024, 1, 1),
                exposure_period_end=date(2024, 12, 31),
                currency="GBP",
                aggregate=True,
            ),
            exposure_values=ExposureValues(
                exposure_value=1.0, attachment_point=0.0, limit=1.0
            ),
        )
        StorageService().save_exposures([e], db)
        conn = sqlite3.connect(db)
        val = conn.execute(
            "SELECT exposure_meta_aggregate FROM exposures WHERE exposure_meta_exposure_id='E-AGG'"
        ).fetchone()[0]
        conn.close()
        assert val == 1

    def test_enum_serialized_as_name(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_exposures([_make_exposure()], db)
        conn = sqlite3.connect(db)
        val = conn.execute(
            "SELECT exposure_meta_exposure_type FROM exposures"
        ).fetchone()[0]
        conn.close()
        assert val == "WRITTEN"

    def test_date_serialized_as_isoformat(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_exposures([_make_exposure()], db)
        conn = sqlite3.connect(db)
        val = conn.execute(
            "SELECT exposure_meta_exposure_period_start FROM exposures"
        ).fetchone()[0]
        conn.close()
        assert val == "2024-01-01"

    def test_empty_list_noop(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_exposures([], db)
        assert not Path(db).exists()


class TestStorageServiceSaveClaims:
    def test_saves_single_claim(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_claims([_make_claim()], db)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT claims_meta_data_claim_id FROM claims"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "CL-001"

    def test_dev_history_pipe_separated(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_claims([_make_claim()], db)
        conn = sqlite3.connect(db)
        val = conn.execute(
            "SELECT claims_development_history_development_months FROM claims"
        ).fetchone()[0]
        conn.close()
        assert val == "12|24"

    def test_uses_uncapped_dev_history(self, tmp_path: Path) -> None:
        # contract_limit=5000 would cap capped_history to 5000; uncapped stays at 11000
        c = Claim(
            claims_meta_data=ClaimsMetaData(
                claim_id="CL-CAP",
                currency="GBP",
                contract_limit=5000.0,
                contract_deductible=0.0,
                claim_in_xs_of_deductible=False,
                claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
                loss_date=date(2022, 1, 1),
                policy_inception_date=date(2022, 1, 1),
                report_date=date(2022, 2, 1),
            ),
            claims_development_history=ClaimDevelopmentHistory(
                development_months=[12],
                cumulative_dev_paid=[4000.0],
                cumulative_dev_incurred=[11000.0],
            ),
        )
        db = str(tmp_path / "test.db")
        StorageService().save_claims([c], db)
        conn = sqlite3.connect(db)
        val = conn.execute(
            "SELECT claims_development_history_cumulative_dev_incurred FROM claims"
        ).fetchone()[0]
        conn.close()
        assert val == "11000.0"  # uncapped, not 5000.0

    def test_upsert_replaces_existing(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        svc = StorageService()
        svc.save_claims([_make_claim("CL-001")], db)
        svc.save_claims([_make_claim("CL-001")], db)
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        conn.close()
        assert count == 1

    def test_empty_list_noop(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_claims([], db)
        assert not Path(db).exists()


class TestStorageServiceListStored:
    def test_list_exposures_returns_ids(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_exposures([_make_exposure("E-001"), _make_exposure("E-002")], db)
        ids = StorageService().list_stored(db, "exposures")
        assert sorted(ids) == ["E-001", "E-002"]

    def test_list_claims_returns_ids(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        StorageService().save_claims([_make_claim("CL-001")], db)
        ids = StorageService().list_stored(db, "claims")
        assert ids == ["CL-001"]

    def test_nonexistent_db_returns_empty(self, tmp_path: Path) -> None:
        db = str(tmp_path / "no_such_file.db")
        assert StorageService().list_stored(db, "exposures") == []

    def test_invalid_table_raises(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")
        with pytest.raises(ValueError, match="Invalid table"):
            StorageService().list_stored(db, "injections")  # type: ignore[arg-type]


class TestRoundTrip:
    def test_exposure_roundtrip(self, tmp_path: Path) -> None:
        db = str(tmp_path / "rt.db")
        StorageService().save_exposures([_make_exposure("E-RT")], db)
        reloaded = DomainService().load_exposures(
            f"sqlite:///{db}", source_type="db", query="SELECT * FROM exposures"
        )
        assert len(reloaded) == 1
        assert reloaded[0].exposure_meta.exposure_id == "E-RT"
        assert reloaded[0].exposure_values.exposure_value == pytest.approx(50000.0)

    def test_claim_roundtrip(self, tmp_path: Path) -> None:
        db = str(tmp_path / "rt.db")
        StorageService().save_claims([_make_claim("CL-RT")], db)
        reloaded = DomainService().load_claims(
            f"sqlite:///{db}", source_type="db", query="SELECT * FROM claims"
        )
        assert len(reloaded) == 1
        assert reloaded[0].claims_meta_data.claim_id == "CL-RT"
        assert reloaded[0].uncapped_claim_development_history.development_months == [12, 24]

    def test_triangle_rebuilt_from_stored_claims(self, tmp_path: Path) -> None:
        db = str(tmp_path / "rt.db")
        StorageService().save_claims([_make_claim("CL-TRI")], db)
        tri = DomainService().build_triangle(str(tmp_path / "rt.db"), source_type="db")
        assert 2022 in tri.origin_years
        assert tri[2022, 12] == pytest.approx(7000.0)
