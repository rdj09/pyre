# tests/test_data_injector/test_domain_schemas/test_claim_schemas.py
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from pyre.claims.claims import Claim, ClaimDevelopmentHistory, ClaimsMetaData
from pyre.data_injector.domain_schemas.claim_schemas import (
    claim_dev_history_schema,
    claim_schema,
    claims_loader,
    claims_meta_schema,
)
from pyre.enums import ClaimYearType


class TestClaimsMetaSchema:
    def test_target_class(self) -> None:
        assert claims_meta_schema.target_class is ClaimsMetaData

    def test_required_fields_present(self) -> None:
        names = [f.name for f in claims_meta_schema.fields]
        assert "claim_id" in names
        assert "currency" in names

    def test_dates_coerced_from_iso_strings(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {
            "claim_id": "CLM-001",
            "currency": "GBP",
            "loss_date": "2020-06-15",
            "policy_inception_date": "2020-01-01",
            "report_date": "2020-07-01",
        }
        meta = Injector(claims_meta_schema).inject(record)
        assert meta.loss_date == date(2020, 6, 15)

    def test_optional_fields_default(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {"claim_id": "CLM-002", "currency": "USD"}
        meta = Injector(claims_meta_schema).inject(record)
        assert meta.contract_limit == pytest.approx(0.0)
        assert meta.claim_in_xs_of_deductible is False
        assert meta.status == "Open"

    def test_claim_year_type_coerced_from_string(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {"claim_id": "CLM-003", "currency": "EUR", "claim_year_basis": "UNDERWRITING_YEAR"}
        meta = Injector(claims_meta_schema).inject(record)
        assert meta.claim_year_basis == ClaimYearType.UNDERWRITING_YEAR


class TestClaimDevHistorySchema:
    def test_target_class(self) -> None:
        assert claim_dev_history_schema.target_class is ClaimDevelopmentHistory

    def test_pipe_separated_lists_parsed(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {
            "development_months": "12|24|36",
            "cumulative_dev_paid": "10000|20000|30000",
            "cumulative_dev_incurred": "15000|25000|35000",
        }
        history = Injector(claim_dev_history_schema).inject(record)
        assert history.development_months == [12, 24, 36]
        assert history.cumulative_dev_paid == pytest.approx([10000.0, 20000.0, 30000.0])

    def test_empty_record_gives_empty_lists(self) -> None:
        from pyre.data_injector.injector import Injector

        history = Injector(claim_dev_history_schema).inject({})
        assert history.development_months == []
        assert history.cumulative_dev_paid == []


class TestClaimSchema:
    def test_nested_keys_match_constructor_args(self) -> None:
        assert "claims_meta_data" in claim_schema.nested
        assert "claims_development_history" in claim_schema.nested

    def test_injects_flat_record(self) -> None:
        from pyre.data_injector.injector import Injector

        record = {
            "claims_meta_data.claim_id": "CLM-004",
            "claims_meta_data.currency": "GBP",
            "claims_meta_data.loss_date": "2021-03-01",
            "claims_meta_data.policy_inception_date": "2021-01-01",
            "claims_meta_data.report_date": "2021-04-01",
            "claims_development_history.development_months": "12|24",
            "claims_development_history.cumulative_dev_paid": "5000|8000",
            "claims_development_history.cumulative_dev_incurred": "7000|10000",
        }
        claim = Injector(claim_schema).inject(record)
        assert isinstance(claim, Claim)
        assert claim.claims_meta_data.claim_id == "CLM-004"
        assert claim._claim_development_history.development_months == [12, 24]


class TestClaimsLoader:
    def test_loads_from_csv(self, tmp_path: Path) -> None:
        csv_text = (
            "claims_meta_data.claim_id,claims_meta_data.currency,"
            "claims_meta_data.loss_date,claims_meta_data.policy_inception_date,"
            "claims_meta_data.report_date,"
            "claims_development_history.development_months,"
            "claims_development_history.cumulative_dev_paid,"
            "claims_development_history.cumulative_dev_incurred\n"
            "CLM-005,GBP,2022-06-01,2022-01-01,2022-07-01,12|24,5000|9000,7000|11000"
        )
        p = tmp_path / "claims.csv"
        p.write_text(csv_text, encoding="utf-8")
        loader = claims_loader()
        results = loader.from_csv(p)
        assert len(results) == 1
        assert results[0].claims_meta_data.claim_id == "CLM-005"
        assert results[0]._claim_development_history.development_months == [12, 24]
