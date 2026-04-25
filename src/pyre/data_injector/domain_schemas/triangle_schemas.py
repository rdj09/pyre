# src/pyre/data_injector/domain_schemas/triangle_schemas.py
"""Triangle loader utilities wrapping the Claims -> Triangle pipeline."""

from __future__ import annotations

from pathlib import Path

from pyre.claims.claims import Claims
from pyre.claims.triangles import Triangle

from ..adapters.csv_adapter import CSVAdapter
from .claim_schemas import claims_loader


def triangle_loader(source: str | Path, value_type: str = "incurred") -> Triangle:
    """Load a CSV of claims and build a Triangle via Triangle.from_claims.

    CSV must use dot-notation columns matching the claim_schema convention.

    Args:
        source: Path to CSV file containing claim rows.
        value_type: 'incurred' or 'paid'.

    Raises:
        ValueError: If value_type is invalid (propagated from Triangle.from_claims).
    """
    if value_type not in ("incurred", "paid"):
        raise ValueError(f"value_type must be 'incurred' or 'paid', got '{value_type}'")
    loader = claims_loader()
    claim_list = loader.from_csv(source)
    claims = Claims(claim_list)
    # Use uncapped development history so that claims loaded without explicit
    # contract limits (contract_limit defaults to 0.0) are not zeroed out by
    # the cap.  The deductible is still applied via uncapped_claim_development_history.
    origin_years = claims.modelling_years
    dev_periods_set: set[int] = set()
    for claim in claims:
        dev_periods_set.update(claim.uncapped_claim_development_history.development_months)
    dev_periods = sorted(dev_periods_set)
    triangle_data: dict[int, dict[int, float | None]] = {year: {} for year in origin_years}
    for claim in claims:
        origin_year = claim.claims_meta_data.modelling_year
        dev_hist = claim.uncapped_claim_development_history
        values = (
            dev_hist.cumulative_dev_incurred
            if value_type == "incurred"
            else dev_hist.cumulative_dev_paid
        )
        for dev_period, value in zip(dev_hist.development_months, values, strict=False):
            if origin_year in triangle_data:
                triangle_data[origin_year][dev_period] = (
                    triangle_data[origin_year].get(dev_period) or 0.0
                ) + value
    return Triangle(triangle=triangle_data, origin_years=origin_years, dev_periods=dev_periods)


def triangle_from_csv(source: str | Path) -> Triangle:
    """Load a pre-formed triangle from wide-format CSV.

    Expected CSV structure:
        origin_year,dev_12,dev_24,dev_36,...

    Column header 'dev_N' is development period N (integer).
    Empty cells become None (not yet observed).
    """
    records = CSVAdapter().load(source)
    if not records:
        return Triangle()
    sample = records[0]
    dev_cols = {k: int(k[4:]) for k in sample if k.startswith("dev_")}
    triangle_data: dict[int, dict[int, float | None]] = {}
    for row in records:
        origin_year = int(row["origin_year"])
        triangle_data[origin_year] = {}
        for col_name, dev_period in dev_cols.items():
            raw = row.get(col_name)
            if raw is None or (isinstance(raw, str) and raw.strip() == ""):
                triangle_data[origin_year][dev_period] = None
            else:
                triangle_data[origin_year][dev_period] = float(raw)
    return Triangle(triangle=triangle_data)
