import unittest
from datetime import date

from pyre import (
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    Exposure,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.models.Experience.experience_preparer import (
    ExperienceModelData,
    summarize_by_layer_year,
    summarize_exposures_by_year,
)
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


def _build_model_data(claims, exposures, layers):
    metadata = RIContractMetadata(
        contract_id="C-0001",
        contract_description="Test",
        cedent_name="Acme Re",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2022, 1, 1),
        expiration_date=date(2022, 12, 31),
        fx_rates={"USD": 1.0},
    )
    contract = RIContract(contract_meta_data=metadata, layers=layers)
    return ExperienceModelData(claims=claims, exposures=exposures, ri_contract=contract)


def _xol_layer():
    return RILayer(
        layer_id=1,
        layer_name="XOL Layer",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=100_000.0,
        occurrence_limit=200_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=0.0,
        subject_lines_of_business=[],
        subject_lob_exposure_amounts=[],
        full_subject_premium=0.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )


def _claim_2022():
    return Claim(
        ClaimsMetaData(
            claim_id="CLM001",
            currency="USD",
            contract_limit=2_000_000.0,
            loss_date=date(2022, 3, 1),
        ),
        ClaimDevelopmentHistory(
            development_months=[12, 24],
            cumulative_dev_paid=[50000.0, 90000.0],
            cumulative_dev_incurred=[120000.0, 250000.0],
        ),
    )


def _claim(claim_id: str, year: int):
    return Claim(
        ClaimsMetaData(
            claim_id=claim_id,
            currency="USD",
            contract_limit=2_000_000.0,
            loss_date=date(year, 3, 1),
        ),
        ClaimDevelopmentHistory(
            development_months=[12],
            cumulative_dev_paid=[50000.0],
            cumulative_dev_incurred=[120000.0],
        ),
    )


def _layer(layer_id: int, layer_name: str):
    return RILayer(
        layer_id=layer_id,
        layer_name=layer_name,
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=0.0,
        occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=0.0,
        subject_lines_of_business=[],
        subject_lob_exposure_amounts=[],
        full_subject_premium=0.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )


def _exposure_2022():
    return Exposure(
        ExposureMetaData(
            exposure_id="EXP2022",
            exposure_name="2022 Premium",
            exposure_period_start=date(2022, 1, 1),
            exposure_period_end=date(2022, 12, 31),
            currency="USD",
        ),
        ExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0),
    )


class TestSummarizeByLayerYear(unittest.TestCase):
    def test_returns_one_row_per_layer_and_year_with_loss_ratio(self):
        model_data = _build_model_data(
            Claims([_claim_2022()]), Exposures([_exposure_2022()]), [_xol_layer()]
        )

        rows = summarize_by_layer_year(model_data)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["layer_id"], 1)
        self.assertEqual(row["layer_name"], "XOL Layer")
        self.assertEqual(row["modelling_year"], 2022)
        self.assertEqual(row["ceded_paid"], 0.0)
        self.assertEqual(row["ceded_incurred"], 150000.0)
        self.assertEqual(row["claim_count"], 1)
        self.assertEqual(row["earned_premium"], 1_000_000.0)
        self.assertAlmostEqual(row["loss_ratio"], 0.15)

    def test_loss_ratio_is_none_when_earned_premium_is_zero(self):
        model_data = _build_model_data(Claims([_claim_2022()]), Exposures([]), [_xol_layer()])

        rows = summarize_by_layer_year(model_data)

        self.assertEqual(rows[0]["earned_premium"], 0.0)
        self.assertIsNone(rows[0]["loss_ratio"])

    def test_no_claims_returns_empty_list_not_an_error(self):
        model_data = _build_model_data(Claims([]), Exposures([_exposure_2022()]), [_xol_layer()])

        rows = summarize_by_layer_year(model_data)

        self.assertEqual(rows, [])

    def test_rows_are_sorted_by_layer_id_then_modelling_year(self):
        claims = Claims([_claim("A", 2021), _claim("B", 2019), _claim("C", 2020)])
        layers = [_layer(2, "Layer 2"), _layer(1, "Layer 1")]
        model_data = _build_model_data(claims, Exposures([]), layers)

        rows = summarize_by_layer_year(model_data)

        self.assertEqual(
            [(r["layer_id"], r["modelling_year"]) for r in rows],
            [(1, 2019), (1, 2020), (1, 2021), (2, 2019), (2, 2020), (2, 2021)],
        )


class TestSummarizeExposuresByYear(unittest.TestCase):
    def test_returns_one_row_per_year(self):
        model_data = _build_model_data(Claims([]), Exposures([_exposure_2022()]), [_xol_layer()])

        rows = summarize_exposures_by_year(model_data)

        self.assertEqual(
            rows, [{"modelling_year": 2022, "written": 1_000_000.0, "earned": 1_000_000.0}]
        )


if __name__ == "__main__":
    unittest.main()
