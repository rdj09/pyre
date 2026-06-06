# tests/conftest.py
from datetime import date

import pytest

from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData
from pyre.enums import ClaimTriggerBasis, ContractType, IndexationClauseType
from pyre.exposures.exposures import Exposure, ExposureMetaData, Exposures, ExposureValues
from pyre.treaty.contracts import RIContract, RIContractMetadata, RILayer


@pytest.fixture
def sample_claim() -> Claim:
    meta = ClaimsMetaData(claim_id="C001", currency="GBP", loss_date=date(2020, 6, 1))
    dev = ClaimDevelopmentHistory([12, 24], [80_000.0, 100_000.0], [90_000.0, 110_000.0])
    return Claim(meta, dev)


@pytest.fixture
def sample_claims(sample_claim: Claim) -> Claims:
    return Claims([sample_claim])


@pytest.fixture
def sample_exposure() -> Exposure:
    meta = ExposureMetaData(
        exposure_id="E001",
        exposure_name="Test",
        exposure_period_start=date(2020, 1, 1),
        exposure_period_end=date(2020, 12, 31),
        currency="GBP",
    )
    vals = ExposureValues(exposure_value=1_000_000.0, attachment_point=0.0, limit=500_000.0)
    return Exposure(meta, vals)


@pytest.fixture
def sample_exposures(sample_exposure: Exposure) -> Exposures:
    return Exposures([sample_exposure])


@pytest.fixture
def sample_layer() -> RILayer:
    return RILayer(
        layer_id=1,
        layer_name="Layer 1",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=500_000.0,
        occurrence_limit=500_000.0,
        aggregate_attachment=0.0,
        aggregate_limit=float("inf"),
        subject_lines_of_business=["ALL"],
        subject_lob_exposure_amounts=[0.0],
        full_subject_premium=100_000.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=1,
        reinstatement_cost={1: 1.0},
    )


@pytest.fixture
def sample_contract(sample_layer: RILayer) -> RIContract:
    meta = RIContractMetadata(
        contract_id="CTR-001",
        contract_description="Test",
        cedent_name="Cedent",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2021, 1, 1),
        expiration_date=date(2021, 12, 31),
        fx_rates={"GBP": 1.0},
    )
    return RIContract(contract_meta_data=meta, layers=[sample_layer])
