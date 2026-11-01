"""Pure-Python service layer bridging UI input (CSV/forms) to pyre domain objects.

Deliberately has no `import panel` — this module is unit-testable without a
running Panel server. Only `app.py` and `app/pages/*.py` should import panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from pyre import (
    Claim,
    ClaimDevelopmentHistory,
    Claims,
    ClaimsMetaData,
    ClaimYearType,
    ExperienceModelData,
    Exposure,
    ExposureBasis,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType

CLAIMS_REQUIRED_COLUMNS = [
    "claim_id",
    "currency",
    "contract_limit",
    "development_month",
    "cumulative_paid",
    "cumulative_incurred",
]

EXPOSURES_REQUIRED_COLUMNS = [
    "exposure_id",
    "exposure_name",
    "exposure_period_start",
    "exposure_period_end",
    "currency",
    "exposure_value",
]


@dataclass
class PricingResults:
    """Output of run_pricing: plain pandas DataFrames, no panel dependency."""

    by_layer_year: pd.DataFrame
    exposures_by_year: pd.DataFrame


def _parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return str(value).strip().lower() in ("true", "1", "yes")


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    parsed: date = pd.to_datetime(value).date()
    return parsed


def parse_claims_csv(path_or_buffer) -> Claims:
    """Build a Claims collection from a long-format CSV (one row per claim/dev-point).

    Raises:
        ValueError: if a required column is missing, or if any claim's
            contract_limit is missing/<= 0 (ClaimsMetaData.contract_limit
            defaults to 0.0, which silently caps every ceded amount to zero).
    """
    df = pd.read_csv(path_or_buffer)

    missing = [c for c in CLAIMS_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"claims CSV is missing required column(s): {', '.join(missing)}")

    claims: list[Claim] = []
    for claim_id, group in df.groupby("claim_id", sort=False):
        first = group.iloc[0]

        contract_limit = first.get("contract_limit")
        if pd.isna(contract_limit) or float(contract_limit) <= 0:
            raise ValueError(
                f"Claim '{claim_id}' needs a contract limit greater than zero "
                f"(currently {'blank' if pd.isna(contract_limit) else contract_limit})."
            )

        claim_year_basis_raw = first.get("claim_year_basis")
        claim_year_basis = (
            ClaimYearType[str(claim_year_basis_raw).strip()]
            if claim_year_basis_raw and not pd.isna(claim_year_basis_raw)
            else ClaimYearType.ACCIDENT_YEAR
        )

        meta = ClaimsMetaData(
            claim_id=str(claim_id),
            currency=str(first["currency"]),
            contract_limit=float(contract_limit),
            contract_deductible=float(first.get("contract_deductible", 0.0) or 0.0),
            claim_in_xs_of_deductible=_parse_bool(first.get("claim_in_xs_of_deductible")),
            claim_year_basis=claim_year_basis,
            loss_date=_parse_date(first.get("loss_date", date(1900, 1, 1))),
            policy_inception_date=_parse_date(first.get("policy_inception_date", date(1900, 1, 1))),
            report_date=_parse_date(first.get("report_date", date(1900, 1, 1))),
            line_of_business=first.get("line_of_business") or None,
            status=first.get("status") or "Open",
        )

        sorted_group = group.sort_values("development_month")
        dev_history = ClaimDevelopmentHistory(
            development_months=sorted_group["development_month"].astype(int).tolist(),
            cumulative_dev_paid=sorted_group["cumulative_paid"].astype(float).tolist(),
            cumulative_dev_incurred=sorted_group["cumulative_incurred"].astype(float).tolist(),
        )

        claims.append(Claim(claims_meta_data=meta, claims_development_history=dev_history))

    return Claims(claims)


def parse_exposures_csv(path_or_buffer) -> Exposures:
    """Build an Exposures collection from a CSV (one row per exposure)."""
    df = pd.read_csv(path_or_buffer)

    missing = [c for c in EXPOSURES_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"exposures CSV is missing required column(s): {', '.join(missing)}")

    exposures: list[Exposure] = []
    for _, row in df.iterrows():
        exposure_type_raw = row.get("exposure_type")
        exposure_type = (
            ExposureBasis[str(exposure_type_raw).strip()]
            if exposure_type_raw and not pd.isna(exposure_type_raw)
            else ExposureBasis.EARNED
        )

        meta = ExposureMetaData(
            exposure_id=str(row["exposure_id"]),
            exposure_name=str(row["exposure_name"]),
            exposure_period_start=_parse_date(row["exposure_period_start"]),
            exposure_period_end=_parse_date(row["exposure_period_end"]),
            currency=str(row["currency"]),
            aggregate=_parse_bool(row.get("aggregate")),
            line_of_business=row.get("line_of_business") or None,
            stacking_id=row.get("stacking_id") or None,
            exposure_type=exposure_type,
            location=row.get("location") or None,
            peril=row.get("peril") or None,
            occupancy=row.get("occupancy") or None,
        )
        values = ExposureValues(
            exposure_value=float(row["exposure_value"]),
            attachment_point=float(row.get("attachment_point", 0.0) or 0.0),
            limit=float(row.get("limit", row["exposure_value"]) or row["exposure_value"]),
        )
        exposures.append(Exposure(exposure_meta=meta, exposure_values=values))

    return Exposures(exposures)


def build_contract_metadata(form: dict[str, Any]) -> RIContractMetadata:
    """Build RIContractMetadata from a flat form-input dict."""
    return RIContractMetadata(
        contract_id=form["contract_id"],
        contract_description=form.get("contract_description", ""),
        cedent_name=form.get("cedent_name", ""),
        trigger_basis=ClaimTriggerBasis[form["trigger_basis"]]
        if isinstance(form["trigger_basis"], str)
        else form["trigger_basis"],
        indexation_clause=IndexationClauseType[form["indexation_clause"]]
        if isinstance(form["indexation_clause"], str)
        else form["indexation_clause"],
        indexation_margin=float(form.get("indexation_margin", 0.0)),
        inception_date=_parse_date(form["inception_date"]),
        expiration_date=_parse_date(form["expiration_date"]),
        fx_rates=form.get("fx_rates") or {"USD": 1.0},
    )


def build_layer(form: dict[str, Any]) -> RILayer:
    """Build an RILayer from a flat form-input dict."""
    layer_type = form["layer_type"]
    if isinstance(layer_type, str):
        layer_type = ContractType[layer_type]

    return RILayer(
        layer_id=int(form["layer_id"]),
        layer_name=form.get("layer_name", f"Layer {form['layer_id']}"),
        layer_type=layer_type,
        occurrence_attachment=float(form.get("occurrence_attachment", 0.0)),
        occurrence_limit=float(form.get("occurrence_limit", 0.0)),
        aggregate_attachment=float(form.get("aggregate_attachment", 0.0)),
        aggregate_limit=float(form.get("aggregate_limit", 0.0)),
        subject_lines_of_business=form.get("subject_lines_of_business", []),
        subject_lob_exposure_amounts=form.get("subject_lob_exposure_amounts", []),
        full_subject_premium=float(form.get("full_subject_premium", 0.0)),
        written_line=float(form.get("written_line", 1.0)),
        signed_line=float(form.get("signed_line", 1.0)),
        number_of_reinstatements=int(form.get("number_of_reinstatements", 0)),
        reinstatement_cost=form.get("reinstatement_cost", {}),
        cession=float(form.get("cession", 1.0)),
    )


def run_pricing(claims: Claims, exposures: Exposures, ri_contract: RIContract) -> PricingResults:
    """Run pyre's experience-rating calculation and shape the output as DataFrames.

    Raises:
        NotImplementedError: if any layer on the contract is SURPLUS_SHARE
            (pyre does not yet support pricing that layer type). Callers
            (the UI) should prevent selecting that layer type rather than
            relying on catching this.
    """
    model_data = ExperienceModelData(claims=claims, exposures=exposures, ri_contract=ri_contract)

    layer_names = {layer.layer_id: layer.layer_name for layer in ri_contract.layers}

    aggregate_claims = model_data.aggregate_subject_contract_claims
    aggregate_exposures = model_data.aggregate_exposures

    rows = []
    for layer_id, year_agg in aggregate_claims.items():
        for modelling_year, values in year_agg.items():
            earned_premium = aggregate_exposures.get(modelling_year, {}).get("earned", 0.0)
            ceded_incurred = values["latest_incurred"]
            loss_ratio = (ceded_incurred / earned_premium) if earned_premium else None
            rows.append(
                {
                    "layer_id": layer_id,
                    "layer_name": layer_names.get(layer_id, str(layer_id)),
                    "modelling_year": modelling_year,
                    "ceded_paid": values["latest_paid"],
                    "ceded_incurred": ceded_incurred,
                    "claim_count": values["total_count"],
                    "earned_premium": earned_premium,
                    "loss_ratio": loss_ratio,
                }
            )

    by_layer_year = pd.DataFrame(
        rows,
        columns=[
            "layer_id",
            "layer_name",
            "modelling_year",
            "ceded_paid",
            "ceded_incurred",
            "claim_count",
            "earned_premium",
            "loss_ratio",
        ],
    ).sort_values(["layer_id", "modelling_year"], ignore_index=True)

    exposures_by_year = pd.DataFrame(
        [
            {"modelling_year": year, "written": v["written"], "earned": v["earned"]}
            for year, v in sorted(aggregate_exposures.items())
        ],
        columns=["modelling_year", "written", "earned"],
    )

    return PricingResults(by_layer_year=by_layer_year, exposures_by_year=exposures_by_year)
