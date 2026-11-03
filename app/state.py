"""Shared, panel-free application state for the treaty pricing workbench.

Deliberately has no `import panel` -- pages mutate an instance of
WorkbenchState and call its methods; only app.py/pages/*.py talk to panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.service import PricingResults
from pyre import Claims, Exposures, RIContract, RIContractMetadata, RILayer


@dataclass
class WorkbenchState:
    contract_metadata: Optional[RIContractMetadata] = None
    layers: list[RILayer] = field(default_factory=list)
    claims: Optional[Claims] = None
    exposures: Optional[Exposures] = None
    results: Optional[PricingResults] = None
    loaded_version_id: Optional[int] = None

    def build_contract(self) -> RIContract:
        if self.contract_metadata is None:
            raise ValueError("Contract metadata has not been configured yet.")
        if not self.layers:
            raise ValueError("At least one layer must be configured.")
        return RIContract(contract_meta_data=self.contract_metadata, layers=self.layers)

    def is_ready_to_price(self) -> bool:
        return (
            self.contract_metadata is not None
            and bool(self.layers)
            and self.claims is not None
            and self.exposures is not None
        )
