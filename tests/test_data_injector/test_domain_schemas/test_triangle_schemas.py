# tests/test_data_injector/test_domain_schemas/test_triangle_schemas.py
from __future__ import annotations

from pathlib import Path

import pytest

from pyre.claims.triangles import Triangle
from pyre.data_injector.domain_schemas.triangle_schemas import (
    triangle_from_csv,
    triangle_loader,
)


class TestTriangleLoader:
    def test_loads_triangle_from_claims_csv(self, tmp_path: Path) -> None:
        csv_text = (
            "claims_meta_data.claim_id,claims_meta_data.currency,"
            "claims_meta_data.loss_date,claims_meta_data.policy_inception_date,"
            "claims_meta_data.report_date,"
            "claims_development_history.development_months,"
            "claims_development_history.cumulative_dev_paid,"
            "claims_development_history.cumulative_dev_incurred\n"
            "CLM-T01,GBP,2020-06-01,2020-01-01,2020-07-01,"
            "12|24|36,10000|15000|18000,12000|18000|21000\n"
            "CLM-T02,GBP,2021-06-01,2021-01-01,2021-07-01,"
            "12|24,8000|13000,10000|16000"
        )
        p = tmp_path / "claims.csv"
        p.write_text(csv_text, encoding="utf-8")
        triangle = triangle_loader(p, value_type="incurred")
        assert isinstance(triangle, Triangle)
        assert 2020 in triangle.origin_years
        assert 2021 in triangle.origin_years
        assert triangle[2020, 12] == pytest.approx(12000.0)
        assert triangle[2020, 36] == pytest.approx(21000.0)

    def test_paid_value_type(self, tmp_path: Path) -> None:
        csv_text = (
            "claims_meta_data.claim_id,claims_meta_data.currency,"
            "claims_meta_data.loss_date,claims_meta_data.policy_inception_date,"
            "claims_meta_data.report_date,"
            "claims_development_history.development_months,"
            "claims_development_history.cumulative_dev_paid,"
            "claims_development_history.cumulative_dev_incurred\n"
            "CLM-T03,GBP,2022-01-01,2022-01-01,2022-02-01,12,5000,7000"
        )
        p = tmp_path / "paid_claims.csv"
        p.write_text(csv_text, encoding="utf-8")
        triangle = triangle_loader(p, value_type="paid")
        assert triangle[2022, 12] == pytest.approx(5000.0)

    def test_invalid_value_type_raises(self, tmp_path: Path) -> None:
        csv_text = (
            "claims_meta_data.claim_id,claims_meta_data.currency,"
            "claims_meta_data.loss_date,claims_meta_data.policy_inception_date,"
            "claims_meta_data.report_date,"
            "claims_development_history.development_months,"
            "claims_development_history.cumulative_dev_paid,"
            "claims_development_history.cumulative_dev_incurred\n"
            "CLM-T04,GBP,2022-01-01,2022-01-01,2022-02-01,12,5000,7000"
        )
        p = tmp_path / "bad.csv"
        p.write_text(csv_text, encoding="utf-8")
        with pytest.raises(ValueError, match="value_type"):
            triangle_loader(p, value_type="reserves")


class TestTriangleFromCSV:
    def test_loads_wide_format_triangle(self, tmp_path: Path) -> None:
        csv_text = (
            "origin_year,dev_12,dev_24,dev_36\n"
            "2020,100000,150000,175000\n"
            "2021,110000,160000,\n"
            "2022,120000,,"
        )
        p = tmp_path / "triangle.csv"
        p.write_text(csv_text, encoding="utf-8")
        triangle = triangle_from_csv(p)
        assert isinstance(triangle, Triangle)
        assert triangle[2020, 12] == pytest.approx(100000.0)
        assert triangle[2020, 36] == pytest.approx(175000.0)
        assert triangle[2021, 36] is None
        assert triangle[2022, 24] is None
