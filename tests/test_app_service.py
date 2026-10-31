import io
import unittest
from datetime import date

from app.service import (
    build_contract_metadata,
    build_layer,
    parse_claims_csv,
    parse_exposures_csv,
    run_pricing,
)
from pyre import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
from pyre import Exposure, ExposureMetaData, Exposures, ExposureValues
from pyre import RIContract
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


CLAIMS_CSV = """claim_id,currency,contract_limit,loss_date,development_month,cumulative_paid,cumulative_incurred
CLM001,USD,2000000,2022-03-01,12,50000,120000
CLM001,USD,2000000,2022-03-01,24,90000,250000
CLM002,USD,2000000,2022-07-10,12,20000,60000
CLM003,USD,2000000,2023-05-15,12,150000,350000
"""

EXPOSURES_CSV = """exposure_id,exposure_name,exposure_period_start,exposure_period_end,currency,exposure_value
EXP2022,2022 Premium,2022-01-01,2022-12-31,USD,1000000
EXP2023,2023 Premium,2023-01-01,2023-12-31,USD,1200000
"""


class TestParseClaimsCsv(unittest.TestCase):
    def test_builds_claims_with_correct_dev_history(self):
        claims = parse_claims_csv(io.StringIO(CLAIMS_CSV))
        self.assertIsInstance(claims, Claims)
        self.assertEqual(sorted(claims.modelling_years), [2022, 2023])

        by_id = {c.claims_meta_data.claim_id: c for c in claims.claims}
        self.assertEqual(
            by_id["CLM001"].capped_claim_development_history.cumulative_dev_paid,
            [50000.0, 90000.0],
        )
        self.assertEqual(
            by_id["CLM001"].capped_claim_development_history.development_months,
            [12, 24],
        )

    def test_rejects_missing_or_zero_contract_limit(self):
        bad_csv = (
            "claim_id,currency,contract_limit,loss_date,development_month,"
            "cumulative_paid,cumulative_incurred\n"
            "CLM001,USD,0,2022-03-01,12,50000,120000\n"
        )
        with self.assertRaises(ValueError):
            parse_claims_csv(io.StringIO(bad_csv))


class TestParseExposuresCsv(unittest.TestCase):
    def test_builds_exposures(self):
        exposures = parse_exposures_csv(io.StringIO(EXPOSURES_CSV))
        self.assertIsInstance(exposures, Exposures)
        self.assertEqual(sorted(exposures.modelling_years), [2022, 2023])


class TestBuildContractAndLayer(unittest.TestCase):
    def test_build_contract_metadata_from_form_dict(self):
        metadata = build_contract_metadata(
            {
                "contract_id": "C-0001",
                "contract_description": "Test",
                "cedent_name": "Acme Re",
                "trigger_basis": "LOD",
                "indexation_clause": "FULL_INDEXATION",
                "indexation_margin": 0.0,
                "inception_date": date(2023, 1, 1),
                "expiration_date": date(2023, 12, 31),
            }
        )
        self.assertEqual(metadata.contract_id, "C-0001")
        self.assertEqual(metadata.trigger_basis, ClaimTriggerBasis.LOD)
        self.assertEqual(metadata.indexation_clause, IndexationClauseType.FULL_INDEXATION)

    def test_build_layer_from_form_dict(self):
        layer = build_layer(
            {
                "layer_id": 1,
                "layer_name": "Layer 1",
                "layer_type": "EXCESS_OF_LOSS",
                "occurrence_attachment": 100000,
                "occurrence_limit": 200000,
            }
        )
        self.assertEqual(layer.layer_type, ContractType.EXCESS_OF_LOSS)
        self.assertEqual(layer.occurrence_attachment, 100000)
        self.assertEqual(layer.occurrence_limit, 200000)


class TestRunPricing(unittest.TestCase):
    def setUp(self):
        self.claims = parse_claims_csv(io.StringIO(CLAIMS_CSV))
        self.exposures = parse_exposures_csv(io.StringIO(EXPOSURES_CSV))
        metadata = build_contract_metadata(
            {
                "contract_id": "C-0001",
                "trigger_basis": "LOD",
                "indexation_clause": "FULL_INDEXATION",
                "inception_date": date(2023, 1, 1),
                "expiration_date": date(2023, 12, 31),
            }
        )
        layer = build_layer(
            {
                "layer_id": 1,
                "layer_name": "XOL Layer",
                "layer_type": "EXCESS_OF_LOSS",
                "occurrence_attachment": 100000,
                "occurrence_limit": 200000,
            }
        )
        self.contract = RIContract(contract_meta_data=metadata, layers=[layer])

    def test_run_pricing_matches_expected_ceded_loss(self):
        results = run_pricing(self.claims, self.exposures, self.contract)
        by_year = results.by_layer_year.set_index("modelling_year")

        self.assertAlmostEqual(by_year.loc[2022, "ceded_paid"], 0.0)
        self.assertAlmostEqual(by_year.loc[2022, "ceded_incurred"], 150000.0)
        self.assertAlmostEqual(by_year.loc[2022, "loss_ratio"], 0.15)

        self.assertAlmostEqual(by_year.loc[2023, "ceded_paid"], 50000.0)
        self.assertAlmostEqual(by_year.loc[2023, "ceded_incurred"], 200000.0)
        self.assertAlmostEqual(by_year.loc[2023, "loss_ratio"], 200000.0 / 1200000.0)

    def test_run_pricing_with_surplus_share_layer_raises(self):
        metadata = build_contract_metadata(
            {
                "contract_id": "C-0002",
                "trigger_basis": "LOD",
                "indexation_clause": "FULL_INDEXATION",
                "inception_date": date(2023, 1, 1),
                "expiration_date": date(2023, 12, 31),
            }
        )
        surplus_layer = build_layer(
            {
                "layer_id": 1,
                "layer_name": "Surplus Layer",
                "layer_type": ContractType.SURPLUS_SHARE,
                "occurrence_attachment": 0,
                "occurrence_limit": 0,
            }
        )
        contract = RIContract(contract_meta_data=metadata, layers=[surplus_layer])
        with self.assertRaises(NotImplementedError):
            run_pricing(self.claims, self.exposures, contract)


if __name__ == "__main__":
    unittest.main()
