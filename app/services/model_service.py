# app/services/model_service.py
"""ModelService — thin facade over pyre model APIs for the Shiny app."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd

from pyre.claims.claims import Claims
from pyre.claims.triangles import IBNERPatternExtractor, Triangle
from pyre.enums import (
    ClaimTriggerBasis,
    ContractType,
    ExposureCurveType,
    FrequencyDistribution,
    IndexationClauseType,
    ProjectionMethods,
    SeverityDistribution,
)
from pyre.exposures.exposures import Exposures
from pyre.models.aggregate.aggregate_features import ModellingAssumptions
from pyre.models.aggregate.simulation_engine import Simulation, SimulationResults
from pyre.models.experience.burn_cost import BurnCostModel
from pyre.models.experience.experience_preparer import ExperienceModelData
from pyre.models.experience.frequency_severity import FrequencyFit, SeverityFit
from pyre.models.exposure.exposure_rating_cost import ExposureModel
from pyre.treaty.contracts import RIContract, RIContractMetadata, RILayer


class ModelService:
    """Stateless facade mapping Shiny widget values to pyre model constructors."""

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def parse_year_factors(self, text: str) -> dict[int, float]:
        """Parse "2020:1.0,2021:1.05" -> {2020: 1.0, 2021: 1.05}."""
        result: dict[int, float] = {}
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            year_str, factor_str = part.split(":", 1)
            result[int(year_str.strip())] = float(factor_str.strip())
        return result

    def parse_fx_rates(self, text: str) -> dict[str, float]:
        """Parse "GBP:1.0,USD:1.25" -> {"GBP": 1.0, "USD": 1.25}."""
        result: dict[str, float] = {}
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            ccy, rate_str = part.split(":", 1)
            result[ccy.strip().upper()] = float(rate_str.strip())
        return result

    def parse_float_list(self, text: str) -> list[float]:
        """Parse "1.0,1.05,1.10" -> [1.0, 1.05, 1.10]."""
        return [float(x.strip()) for x in text.split(",") if x.strip()]

    def parse_str_list(self, text: str) -> list[str]:
        """Parse "CAS,MAT" -> ["CAS", "MAT"]."""
        return [x.strip() for x in text.split(",") if x.strip()]

    def parse_reinstatement_cost(self, text: str) -> dict[int, float]:
        """Parse "1:1.0,2:0.5" -> {1: 1.0, 2: 0.5}."""
        result: dict[int, float] = {}
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            n_str, cost_str = part.split(":", 1)
            result[int(n_str.strip())] = float(cost_str.strip())
        return result

    # ------------------------------------------------------------------
    # Contract building
    # ------------------------------------------------------------------

    def build_contract(
        self,
        contract_id: str,
        contract_description: str,
        cedent_name: str,
        trigger_basis: str,
        indexation_clause: str,
        indexation_margin: float,
        inception_date: date,
        expiration_date: date,
        fx_rates_text: str,
        layers_data: list[dict[str, Any]],
    ) -> RIContract:
        meta = RIContractMetadata(
            contract_id=contract_id,
            contract_description=contract_description,
            cedent_name=cedent_name,
            trigger_basis=ClaimTriggerBasis[trigger_basis],
            indexation_clause=IndexationClauseType[indexation_clause],
            indexation_margin=indexation_margin,
            inception_date=inception_date,
            expiration_date=expiration_date,
            fx_rates=self.parse_fx_rates(fx_rates_text) if fx_rates_text.strip() else {"GBP": 1.0},
        )
        layers = [self._build_layer(i + 1, ld) for i, ld in enumerate(layers_data)]
        return RIContract(contract_meta_data=meta, layers=layers)

    def _build_layer(self, layer_id: int, ld: dict[str, Any]) -> RILayer:
        agg_limit_raw = float(ld.get("aggregate_limit", 0))
        return RILayer(
            layer_id=layer_id,
            layer_name=str(ld.get("layer_name", f"Layer {layer_id}")),
            layer_type=ContractType[str(ld.get("layer_type", "EXCESS_OF_LOSS"))],
            occurrence_attachment=float(ld.get("occurrence_attachment", 0)),
            occurrence_limit=float(ld.get("occurrence_limit", 0)),
            aggregate_attachment=float(ld.get("aggregate_attachment", 0)),
            aggregate_limit=float("inf") if agg_limit_raw == 0 else agg_limit_raw,
            subject_lines_of_business=self.parse_str_list(str(ld.get("subject_lob", "ALL"))),
            subject_lob_exposure_amounts=self.parse_float_list(
                str(ld.get("subject_lob_amounts", "0"))
            ),
            full_subject_premium=float(ld.get("full_subject_premium", 0)),
            written_line=float(ld.get("written_line", 1.0)),
            signed_line=float(ld.get("signed_line", 1.0)),
            number_of_reinstatements=int(ld.get("number_of_reinstatements", 0)),
            reinstatement_cost=self.parse_reinstatement_cost(
                str(ld.get("reinstatement_cost", "1:1.0"))
            ),
            cession=float(ld.get("cession", 1.0)),
        )

    def build_contract_from_json(self, json_bytes: bytes) -> RIContract:
        data = json.loads(json_bytes.decode("utf-8"))
        meta_raw = data["contract_meta_data"]
        meta = RIContractMetadata(
            contract_id=meta_raw["contract_id"],
            contract_description=meta_raw.get("contract_description", ""),
            cedent_name=meta_raw.get("cedent_name", ""),
            trigger_basis=ClaimTriggerBasis[meta_raw["trigger_basis"]],
            indexation_clause=IndexationClauseType[
                meta_raw.get("indexation_clause", "FULL_INDEXATION")
            ],
            indexation_margin=float(meta_raw.get("indexation_margin", 0.0)),
            inception_date=date.fromisoformat(meta_raw["inception_date"]),
            expiration_date=date.fromisoformat(meta_raw["expiration_date"]),
            fx_rates=meta_raw.get("fx_rates", {"GBP": 1.0}),
        )
        layers = [self._build_layer(i + 1, ld) for i, ld in enumerate(data["layers"])]
        return RIContract(contract_meta_data=meta, layers=layers)

    # ------------------------------------------------------------------
    # Experience
    # ------------------------------------------------------------------

    def build_experience_data(
        self,
        claims: Claims,
        exposures: Exposures,
        contract: RIContract,
        exposure_trends: dict[int, float],
        claim_trends: dict[int, float] | None = None,
    ) -> ExperienceModelData:
        return ExperienceModelData(
            claims=claims,
            exposures=exposures,
            ri_contract=contract,
            exposure_trend_factors=exposure_trends,
            claim_trend_factors=claim_trends,
        )

    def run_burn_cost(
        self,
        model_data: ExperienceModelData,
        layer_id: int,
        projection_method: str,
        dev_pattern: dict[int, float],
        a_priori: dict[int, float] | None = None,
    ) -> dict[int, float]:
        method_enum = ProjectionMethods[projection_method]
        years = model_data.exposures.modelling_years
        proj_methods = {y: method_enum for y in years}
        model = BurnCostModel(
            model_data=model_data,
            layer_id=layer_id,
            projection_methods=proj_methods,
            development_pattern=dev_pattern if dev_pattern else None,
            a_priori_assumption=a_priori,
        )
        return model.calculate_burn_cost()

    # ------------------------------------------------------------------
    # Exposure rating
    # ------------------------------------------------------------------

    def build_exposure_model(
        self,
        exposures: Exposures,
        contract: RIContract,
        curve_type_str: str,
        curve_params: dict[str, Any],
    ) -> ExposureModel:
        return ExposureModel(
            exposures=exposures,
            ri_contract=contract,
            selected_curve=ExposureCurveType[curve_type_str],
            curve_parameters=curve_params,
        )

    def run_exposure_rate(
        self, model: ExposureModel, analysis_date: date
    ) -> dict[int, float]:
        return model.calculate_exposure_rate(analysis_date)

    # ------------------------------------------------------------------
    # Triangle IBNER
    # ------------------------------------------------------------------

    def extract_ibner(self, triangle: Triangle) -> dict[int, float | None]:
        return IBNERPatternExtractor(triangle).get_IBNER_pattern()

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def run_simulation(
        self,
        experience_data: ExperienceModelData,
        assumptions: ModellingAssumptions,
        n_simulations: int,
        random_seed: int | None,
        ibner_pattern: dict[int, float | None],
    ) -> SimulationResults:
        clean_ibner: dict[int, float] = {
            k: v for k, v in ibner_pattern.items() if v is not None
        }
        freq_fit = FrequencyFit(
            distributions=[FrequencyDistribution.POISSON],
            data=experience_data,
        )
        sev_fit = SeverityFit(
            distributions=[SeverityDistribution.LOGNORMAL],
            data=experience_data,
            ibner_dev_pattern=clean_ibner,
        )
        sim = Simulation(
            frequency_fit=freq_fit,
            severity_fit=sev_fit,
            ri_contract=experience_data.ri_contract,
            assumptions=assumptions,
            n_simulations=n_simulations,
            random_seed=random_seed,
        )
        sim.run()
        return sim.output()

    def simulation_results_to_df(
        self, results: SimulationResults, contract: RIContract
    ) -> pd.DataFrame:
        layer_names = {layer.layer_id: layer.layer_name for layer in contract.layers}
        rows = []
        for lid in results.loss_cost_by_layer:
            rows.append({
                "layer_id": lid,
                "layer_name": layer_names.get(lid, str(lid)),
                "loss_cost": results.loss_cost_by_layer[lid],
                "required_capital": results.required_capital_by_layer[lid],
                "required_premium": results.required_premium_by_layer[lid],
            })
        df = pd.DataFrame(rows)
        df.loc[len(df)] = {
            "layer_id": -1,
            "layer_name": "PROGRAMME TOTAL",
            "loss_cost": sum(results.loss_cost_by_layer.values()),
            "required_capital": sum(results.required_capital_by_layer.values()),
            "required_premium": results.required_premium_programme,
        }
        return df
