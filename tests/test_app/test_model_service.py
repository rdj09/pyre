# tests/test_app/test_model_service.py
from __future__ import annotations

import json
import math
from datetime import date

import pytest

from app.services.model_service import ModelService


class TestParsers:
    def test_parse_year_factors(self) -> None:
        svc = ModelService()
        result = svc.parse_year_factors("2020:1.0, 2021:1.05")
        assert result == {2020: 1.0, 2021: 1.05}

    def test_parse_fx_rates(self) -> None:
        svc = ModelService()
        result = svc.parse_fx_rates("GBP:1.0,USD:1.25")
        assert result == {"GBP": 1.0, "USD": 1.25}

    def test_parse_float_list(self) -> None:
        svc = ModelService()
        result = svc.parse_float_list("1.0,1.05,1.10")
        assert result == pytest.approx([1.0, 1.05, 1.10])

    def test_parse_str_list(self) -> None:
        svc = ModelService()
        assert svc.parse_str_list("CAS,MAT") == ["CAS", "MAT"]

    def test_parse_reinstatement_cost(self) -> None:
        svc = ModelService()
        result = svc.parse_reinstatement_cost("1:1.0,2:0.5")
        assert result == {1: 1.0, 2: 0.5}


class TestBuildContract:
    def test_build_contract_from_form(self) -> None:
        svc = ModelService()
        contract = svc.build_contract(
            contract_id="TEST-001",
            contract_description="Test",
            cedent_name="Cedent",
            trigger_basis="LOD",
            indexation_clause="FULL_INDEXATION",
            indexation_margin=0.0,
            inception_date=date(2024, 1, 1),
            expiration_date=date(2024, 12, 31),
            fx_rates_text="GBP:1.0",
            layers_data=[{
                "layer_name": "Layer 1",
                "layer_type": "EXCESS_OF_LOSS",
                "occurrence_attachment": 500000,
                "occurrence_limit": 500000,
                "aggregate_attachment": 0,
                "aggregate_limit": 0,
                "subject_lob": "ALL",
                "subject_lob_amounts": "0",
                "full_subject_premium": 1000000,
                "written_line": 1.0,
                "signed_line": 1.0,
                "number_of_reinstatements": 1,
                "reinstatement_cost": "1:1.0",
            }],
        )
        assert contract.contract_meta_data.contract_id == "TEST-001"
        assert len(contract.layers) == 1
        assert contract.layers[0].occurrence_attachment == 500000
        assert math.isinf(contract.layers[0].aggregate_limit)

    def test_build_contract_from_json(self) -> None:
        svc = ModelService()
        payload = {
            "contract_meta_data": {
                "contract_id": "JSON-001",
                "contract_description": "JSON Test",
                "cedent_name": "JSON Cedent",
                "trigger_basis": "LOD",
                "indexation_clause": "FULL_INDEXATION",
                "indexation_margin": 0.0,
                "inception_date": "2024-01-01",
                "expiration_date": "2024-12-31",
                "fx_rates": {"GBP": 1.0},
            },
            "layers": [{
                "layer_id": 1,
                "layer_name": "Layer 1",
                "layer_type": "EXCESS_OF_LOSS",
                "occurrence_attachment": 250000,
                "occurrence_limit": 250000,
                "aggregate_attachment": 0,
                "aggregate_limit": 1000000,
                "subject_lob": "ALL",
                "subject_lob_amounts": "0",
                "full_subject_premium": 500000,
                "written_line": 1.0,
                "signed_line": 1.0,
                "number_of_reinstatements": 0,
                "reinstatement_cost": "1:1.0",
            }],
        }
        contract = svc.build_contract_from_json(json.dumps(payload).encode())
        assert contract.contract_meta_data.contract_id == "JSON-001"
        assert contract.layers[0].aggregate_limit == 1000000


class TestExtractIbner:
    def test_extract_ibner_returns_dict(self) -> None:
        from pyre.claims.triangles import Triangle
        svc = ModelService()
        tri = Triangle(triangle={
            2020: {12: 100.0, 24: 150.0, 36: 175.0},
            2021: {12: 110.0, 24: 160.0},
            2022: {12: 120.0},
        })
        result = svc.extract_ibner(tri)
        assert isinstance(result, dict)
        assert 12 in result
