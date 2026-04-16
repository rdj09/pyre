import pytest
from datetime import date
from pyre.models.exposure.exposure_rating_cost import ExposureModel
from pyre.models.exposure.exposure_curve_functions import ExposureCurveType, swissRe_c_values
from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues, ExposureBasis
from pyre.treaty.contracts import RILayer, RIContractMetadata, RIContract, ClaimTriggerBasis, IndexationClauseType
from pyre.treaty.contract_types import ContractType


def _make_exposure_model() -> ExposureModel:
    exp_meta = ExposureMetaData(
        exposure_id="E1",
        exposure_name="Policy 1",
        exposure_period_start=date(2020, 1, 1),
        exposure_period_end=date(2020, 12, 31),
        currency="GBP",
        exposure_type=ExposureBasis.EARNED,
    )
    # Policy: 0 attachment, 5m limit. Treaty: 1m xs 1m.
    exp_vals = ExposureValues(
        exposure_value=1_000_000.0,
        attachment_point=0.0,
        limit=5_000_000.0,
    )
    exposures = Exposures([Exposure(exp_meta, exp_vals)])

    layer = RILayer(
        layer_id=1,
        layer_name="1m xs 1m",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=1_000_000.0,
        occurrence_limit=1_000_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[5_000_000.0],
        full_subject_premium=100_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=1,
        reinstatement_cost={1: 1.0},
    )
    contract_meta = RIContractMetadata(
        contract_id="CTR001",
        contract_description="Test",
        cedent_name="Test Cedent",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2021, 1, 1),
        expiration_date=date(2021, 12, 31),
        fx_rates={"GBP": 1.0},
    )
    contract = RIContract(contract_meta_data=contract_meta, layers=[layer])

    return ExposureModel(
        exposures=exposures,
        ri_contract=contract,
        selected_curve=ExposureCurveType.MBBEFD,
        curve_parameters={"curve": swissRe_c_values.COMMERCIAL_LINES_MEDIUM},
    )


def test_exposure_share_is_populated_for_all_layers():
    """Regression: _calculate_single_exposure_share() had shares assignment
    inside a misplaced else branch — shares were never populated for policies
    where treaty_layer_limit + treaty_layer_attachment >= policy_limit."""
    model = _make_exposure_model()
    exposures = model._exposures

    for exposure in exposures:
        shares = model._calculate_single_exposure_share(exposure)
        assert isinstance(shares, dict)
        assert len(shares) == 1  # one layer
        assert 1 in shares
        assert 0.0 <= shares[1] <= 1.0
