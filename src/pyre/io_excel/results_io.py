from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from ..models.Experience.experience_preparer import (
    summarize_by_layer_year,
    summarize_exposures_by_year,
)
from ._workbook import write_table

if TYPE_CHECKING:
    from ..models.Experience.experience_preparer import ExperienceModelData
    from ..models.Exposure.exposure_rating_cost import ExposureModel

BY_LAYER_YEAR_COLUMNS = [
    "layer_id", "layer_name", "modelling_year", "ceded_paid",
    "ceded_incurred", "claim_count", "earned_premium", "loss_ratio",
]


def write_experience_rating_results(
    model_data: "ExperienceModelData", path: str | Path | BinaryIO
) -> None:
    """Write an ExperienceModelData's aggregated results to two sheets of one .xlsx workbook.

    "ByLayerYear": one row per (layer_id, modelling_year), including loss_ratio.
    "ExposuresByYear": one row per modelling_year.
    """
    by_layer_year_rows = summarize_by_layer_year(model_data)
    write_table(
        headers=BY_LAYER_YEAR_COLUMNS,
        rows=[[row[col] for col in BY_LAYER_YEAR_COLUMNS] for row in by_layer_year_rows],
        path=path,
        sheet_name="ByLayerYear",
    )

    exposures_rows = summarize_exposures_by_year(model_data)
    write_table(
        headers=["modelling_year", "written", "earned"],
        rows=[[row["modelling_year"], row["written"], row["earned"]] for row in exposures_rows],
        path=path,
        sheet_name="ExposuresByYear",
    )


def write_exposure_rating_results(exposure_model: "ExposureModel", path: str | Path | BinaryIO) -> None:
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
