import unittest
from datetime import date

from app.pages.contract_config import LAYER_COLUMNS, build_contract_config_page
from app.pages.data_loading import build_data_loading_page
from app.state import WorkbenchState
from pyre import RIContractMetadata, RILayer
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType


class TestContractConfigSeeding(unittest.TestCase):
    def test_seeds_widgets_from_existing_contract_metadata_and_layers(self):
        metadata = RIContractMetadata(
            contract_id="C-9999", contract_description="Seeded", cedent_name="Acme Re",
            trigger_basis=ClaimTriggerBasis.LOD, indexation_clause=IndexationClauseType.FULL_INDEXATION,
            indexation_margin=0.0, inception_date=date(2024, 1, 1), expiration_date=date(2024, 12, 31),
            fx_rates={"USD": 1.0},
        )
        layer = RILayer(
            layer_id=1, layer_name="Seeded Layer", layer_type=ContractType.EXCESS_OF_LOSS,
            occurrence_attachment=100_000.0, occurrence_limit=200_000.0, aggregate_attachment=0.0,
            aggregate_limit=0.0, subject_lines_of_business=[], subject_lob_exposure_amounts=[],
            full_subject_premium=0.0, written_line=1.0, signed_line=1.0,
            number_of_reinstatements=0, reinstatement_cost={},
        )
        state = WorkbenchState(contract_metadata=metadata, layers=[layer])

        page = build_contract_config_page(state)
        widgets = {w.name: w for row in page if hasattr(row, "__iter__") for w in row if hasattr(w, "name")}

        self.assertEqual(widgets["Contract ID"].value, "C-9999")
        self.assertEqual(widgets["Cedent"].value, "Acme Re")
        layer_table = next(obj for obj in page if getattr(obj, "name", None) == "Layers")
        self.assertEqual(layer_table.value.iloc[0]["layer_name"], "Seeded Layer")

    def test_defaults_unchanged_when_state_is_empty(self):
        page = build_contract_config_page(WorkbenchState())
        widgets = {w.name: w for row in page if hasattr(row, "__iter__") for w in row if hasattr(w, "name")}
        self.assertEqual(widgets["Contract ID"].value, "C-0001")


class TestDataLoadingSeeding(unittest.TestCase):
    def test_status_reflects_preloaded_claims_and_exposures_on_build(self):
        from app.service import parse_claims_csv, parse_exposures_csv
        import io

        state = WorkbenchState(
            claims=parse_claims_csv(io.StringIO(
                "claim_id,currency,contract_limit,loss_date,development_month,cumulative_paid,cumulative_incurred\n"
                "C1,USD,1000000,2022-01-01,12,100,200\n"
            )),
            exposures=parse_exposures_csv(io.StringIO(
                "exposure_id,exposure_name,exposure_period_start,exposure_period_end,currency,exposure_value\n"
                "E1,E1,2022-01-01,2022-12-31,USD,1000000\n"
            )),
        )

        page = build_data_loading_page(state)
        status = next(obj for obj in page if hasattr(obj, "alert_type"))

        self.assertEqual(status.alert_type, "success")
