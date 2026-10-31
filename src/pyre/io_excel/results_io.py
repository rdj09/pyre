from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._workbook import write_table

if TYPE_CHECKING:
    from ..models.Experience.experience_preparer import ExperienceModelData
    from ..models.Exposure.exposure_rating_cost import ExposureModel


def write_experience_rating_results(model_data: "ExperienceModelData", path: str | Path) -> None:
    """Write an ExperienceModelData's aggregated results to two sheets of one .xlsx workbook.

    "ByLayerYear": one row per (layer_id, modelling_year).
    "ExposuresByYear": one row per modelling_year.
    """
    layer_names = {layer.layer_id: layer.layer_name for layer in model_data.ri_contract.layers}
    aggregate_claims = model_data.aggregate_subject_contract_claims
    aggregate_exposures = model_data.aggregate_exposures

    by_layer_year_rows = []
    for layer_id, year_agg in aggregate_claims.items():
        for modelling_year, values in year_agg.items():
            earned_premium = aggregate_exposures.get(modelling_year, {}).get("earned", 0.0)
            by_layer_year_rows.append(
                [
                    layer_id,
                    layer_names.get(layer_id, str(layer_id)),
                    modelling_year,
                    values["latest_paid"],
                    values["latest_incurred"],
                    values["total_count"],
                    earned_premium,
                ]
            )

    write_table(
        headers=[
            "layer_id",
            "layer_name",
            "modelling_year",
            "ceded_paid",
            "ceded_incurred",
            "claim_count",
            "earned_premium",
        ],
        rows=by_layer_year_rows,
        path=path,
        sheet_name="ByLayerYear",
    )

    exposures_rows = [
        [year, values["written"], values["earned"]]
        for year, values in sorted(aggregate_exposures.items())
    ]
    write_table(
        headers=["modelling_year", "written", "earned"],
        rows=exposures_rows,
        path=path,
        sheet_name="ExposuresByYear",
    )


def write_exposure_rating_results(exposure_model: "ExposureModel", path: str | Path) -> None:
    """Write ExposureModel.calculate_all_shares() to one 'ExposureShares' sheet."""
    shares = exposure_model.calculate_all_shares()

    rows = [
        [exposure_id, layer_id, share]
        for exposure_id, layer_shares in shares.items()
        for layer_id, share in layer_shares.items()
    ]

    write_table(
        headers=["exposure_id", "layer_id", "share"],
        rows=rows,
        path=path,
        sheet_name="ExposureShares",
    )
