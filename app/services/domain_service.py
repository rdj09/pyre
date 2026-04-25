# app/services/domain_service.py
"""DomainService wraps data_injector domain_schemas for use in the Shiny app."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pyre.claims.claims import Claims
from pyre.claims.triangles import Triangle
from pyre.data_injector.domain_schemas.claim_schemas import claims_db_loader, claims_loader
from pyre.data_injector.domain_schemas.exposure_schemas import exposures_db_loader, exposures_loader
from pyre.data_injector.domain_schemas.triangle_schemas import triangle_loader
from pyre.exposures.exposures import Exposures


class DomainService:
    """Stateless facade mapping UI source_type strings to domain schema loaders."""

    def load_exposures(
        self,
        source: Any,
        source_type: str,
        *,
        query: str = "",
        sheet_name: str | int = 0,
    ) -> Exposures:
        """Load and return an Exposures container.

        Args:
            source: File path or data object depending on source_type.
            source_type: One of 'csv', 'excel', 'json', 'yaml', 'dict', 'db'.
            query: SQL query; required when source_type='db'.
            sheet_name: Sheet index/name; used when source_type='excel'.
        """
        loader = exposures_loader()
        match source_type.lower():
            case "csv":
                items = loader.from_csv(Path(str(source)))
            case "excel":
                items = loader.from_excel(Path(str(source)), sheet_name=sheet_name)
            case "json":
                items = loader.from_json(source)
            case "yaml":
                items = loader.from_yaml(Path(str(source)))
            case "dict":
                items = loader.from_dict(source)
            case "db":
                items = exposures_db_loader().from_db(str(source), query)
            case _:
                raise ValueError(
                    f"Unsupported source_type '{source_type}'. "
                    "Expected: csv, excel, json, yaml, dict, db."
                )
        return Exposures(items)

    def load_claims(
        self,
        source: Any,
        source_type: str,
        *,
        query: str = "",
        sheet_name: str | int = 0,
    ) -> Claims:
        """Load and return a Claims container."""
        loader = claims_loader()
        match source_type.lower():
            case "csv":
                items = loader.from_csv(Path(str(source)))
            case "excel":
                items = loader.from_excel(Path(str(source)), sheet_name=sheet_name)
            case "json":
                items = loader.from_json(source)
            case "yaml":
                items = loader.from_yaml(Path(str(source)))
            case "dict":
                items = loader.from_dict(source)
            case "db":
                items = claims_db_loader().from_db(str(source), query)
            case _:
                raise ValueError(
                    f"Unsupported source_type '{source_type}'. "
                    "Expected: csv, excel, json, yaml, dict, db."
                )
        return Claims(items)

    def build_triangle(
        self,
        source: Any,
        source_type: str,
        value_type: str = "incurred",
    ) -> Triangle:
        """Build a Triangle from a claims CSV source."""
        if source_type.lower() != "csv":
            raise ValueError(
                f"Triangle building from source_type='{source_type}' is not supported. "
                "Only 'csv' is supported."
            )
        return triangle_loader(Path(str(source)), value_type=value_type)

    def exposure_summary(self, exposures: Exposures) -> dict[str, Any]:
        """Return summary statistics for an Exposures container."""
        if len(exposures) == 0:
            return {"count": 0, "total_exposure_value": 0.0, "currencies": []}
        return {
            "count": len(exposures),
            "total_exposure_value": sum(e.exposure_values.exposure_value for e in exposures),
            "currencies": sorted(exposures.currencies),
            "modelling_years": exposures.modelling_years,
        }

    def claim_summary(self, claims: Claims) -> dict[str, Any]:
        """Return summary statistics for a Claims container."""
        if len(claims) == 0:
            return {"count": 0, "total_latest_incurred": 0.0, "currencies": []}
        return {
            "count": len(claims),
            "total_latest_incurred": sum(
                c.capped_claim_development_history.latest_incurred for c in claims
            ),
            "total_latest_paid": sum(
                c.capped_claim_development_history.latest_paid for c in claims
            ),
            "currencies": sorted(claims.currencies),
            "modelling_years": claims.modelling_years,
        }
