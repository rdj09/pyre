# tests/test_app/test_domain_service.py
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.services.domain_service import DomainService
from pyre.claims.claims import Claims
from pyre.claims.triangles import Triangle
from pyre.exposures.exposures import Exposures


class TestDomainServiceExposures:
    def test_load_exposures_from_csv(self, tmp_path: Path) -> None:
        csv_text = (
            "exposure_meta.exposure_id,exposure_meta.exposure_name,"
            "exposure_meta.exposure_period_start,exposure_meta.exposure_period_end,"
            "exposure_meta.currency,exposure_values.exposure_value,"
            "exposure_values.attachment_point,exposure_values.limit\n"
            "SVC-E1,Service Test,2024-01-01,2024-12-31,GBP,100000,5000,50000"
        )
        p = tmp_path / "exp.csv"
        p.write_text(csv_text, encoding="utf-8")
        svc = DomainService()
        exposures = svc.load_exposures(str(p), source_type="csv")
        assert isinstance(exposures, Exposures)
        assert len(exposures) == 1
        assert exposures[0].exposure_meta.exposure_id == "SVC-E1"

    def test_load_exposures_from_dict(self) -> None:
        records = [
            {
                "exposure_meta": {
                    "exposure_id": "SVC-E2",
                    "exposure_name": "Dict Test",
                    "exposure_period_start": "2024-01-01",
                    "exposure_period_end": "2024-12-31",
                    "currency": "USD",
                },
                "exposure_values": {
                    "exposure_value": 200000.0,
                    "attachment_point": 10000.0,
                    "limit": 100000.0,
                },
            }
        ]
        svc = DomainService()
        exposures = svc.load_exposures(records, source_type="dict")
        assert len(exposures) == 1
        assert exposures[0].exposure_meta.currency == "USD"

    def test_unsupported_source_type_raises(self) -> None:
        svc = DomainService()
        with pytest.raises(ValueError, match="Unsupported source_type"):
            svc.load_exposures("anything", source_type="parquet")


class TestDomainServiceClaims:
    def test_load_claims_from_csv(self, tmp_path: Path) -> None:
        csv_text = (
            "claims_meta_data.claim_id,claims_meta_data.currency,"
            "claims_meta_data.loss_date,claims_meta_data.policy_inception_date,"
            "claims_meta_data.report_date,"
            "claims_development_history.development_months,"
            "claims_development_history.cumulative_dev_paid,"
            "claims_development_history.cumulative_dev_incurred\n"
            "SVC-C1,GBP,2022-06-01,2022-01-01,2022-07-01,12|24,5000|9000,7000|11000"
        )
        p = tmp_path / "claims.csv"
        p.write_text(csv_text, encoding="utf-8")
        svc = DomainService()
        claims = svc.load_claims(str(p), source_type="csv")
        assert isinstance(claims, Claims)
        assert len(claims) == 1
        assert claims[0].claims_meta_data.claim_id == "SVC-C1"

    def test_load_claims_from_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "svc_claims.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE claims ("
            "claims_meta_data_claim_id TEXT, claims_meta_data_currency TEXT,"
            "claims_meta_data_loss_date TEXT, claims_meta_data_policy_inception_date TEXT,"
            "claims_meta_data_report_date TEXT,"
            "claims_development_history_development_months TEXT,"
            "claims_development_history_cumulative_dev_paid TEXT,"
            "claims_development_history_cumulative_dev_incurred TEXT)"
        )
        conn.execute(
            "INSERT INTO claims VALUES (?,?,?,?,?,?,?,?)",
            (
                "SVC-C2",
                "USD",
                "2021-03-01",
                "2021-01-01",
                "2021-04-01",
                "12|24",
                "6000|10000",
                "8000|13000",
            ),
        )
        conn.commit()
        conn.close()
        svc = DomainService()
        claims = svc.load_claims(
            f"sqlite:///{db_path}",
            source_type="db",
            query="SELECT * FROM claims",
        )
        assert isinstance(claims, Claims)
        assert len(claims) == 1
        assert claims[0].claims_meta_data.claim_id == "SVC-C2"


class TestDomainServiceTriangle:
    def test_build_triangle_from_claims_csv(self, tmp_path: Path) -> None:
        csv_text = (
            "claims_meta_data.claim_id,claims_meta_data.currency,"
            "claims_meta_data.loss_date,claims_meta_data.policy_inception_date,"
            "claims_meta_data.report_date,"
            "claims_development_history.development_months,"
            "claims_development_history.cumulative_dev_paid,"
            "claims_development_history.cumulative_dev_incurred\n"
            "SVC-T1,GBP,2020-06-01,2020-01-01,2020-07-01,12|24,8000|14000,10000|17000"
        )
        p = tmp_path / "tri_claims.csv"
        p.write_text(csv_text, encoding="utf-8")
        svc = DomainService()
        triangle = svc.build_triangle(str(p), source_type="csv", value_type="incurred")
        assert isinstance(triangle, Triangle)
        assert triangle[2020, 12] == pytest.approx(10000.0)

    def test_exposure_summary_returns_dict(self, tmp_path: Path) -> None:
        csv_text = (
            "exposure_meta.exposure_id,exposure_meta.exposure_name,"
            "exposure_meta.exposure_period_start,exposure_meta.exposure_period_end,"
            "exposure_meta.currency,exposure_values.exposure_value,"
            "exposure_values.attachment_point,exposure_values.limit\n"
            "SVC-E3,Summary Test,2024-01-01,2024-12-31,GBP,300000,15000,150000"
        )
        p = tmp_path / "sum_exp.csv"
        p.write_text(csv_text, encoding="utf-8")
        svc = DomainService()
        exposures = svc.load_exposures(str(p), source_type="csv")
        summary = svc.exposure_summary(exposures)
        assert summary["count"] == 1
        assert summary["total_exposure_value"] == pytest.approx(300000.0)

    def test_claim_summary_returns_dict(self, tmp_path: Path) -> None:
        csv_text = (
            "claims_meta_data.claim_id,claims_meta_data.currency,"
            "claims_meta_data.loss_date,claims_meta_data.policy_inception_date,"
            "claims_meta_data.report_date,"
            "claims_development_history.development_months,"
            "claims_development_history.cumulative_dev_paid,"
            "claims_development_history.cumulative_dev_incurred\n"
            "SVC-C3,GBP,2022-01-01,2022-01-01,2022-02-01,12,5000,7000"
        )
        p = tmp_path / "sum_claims.csv"
        p.write_text(csv_text, encoding="utf-8")
        svc = DomainService()
        claims = svc.load_claims(str(p), source_type="csv")
        summary = svc.claim_summary(claims)
        assert summary["count"] == 1
        assert "total_latest_incurred" in summary
