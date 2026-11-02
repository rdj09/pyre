from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...treaty.contracts import RIContract

if TYPE_CHECKING:
    from .simulation_engine import Simulation


@dataclass
class ModellingAssumptions:
    """Pricing assumptions driving a :class:`Simulation` and its downstream
    required-premium calculation.

    ``capital_confidence_level`` defaults to 0.995 -- a commonly used
    convention in practice (e.g. Solvency II's 1-in-200 standard) -- rather
    than a figure mandated by any particular capital-allocation methodology.
    ``use_tvar`` selects between TVaR (expected shortfall, the default) and
    VaR for the tail statistic underlying :meth:`Simulation.required_capital`.
    """

    cost_of_capital: float
    required_rate_of_return: float
    capital_confidence_level: float = 0.995
    use_tvar: bool = True
    investment_yield: float = 0.0
    tax_rate: float = 0.0
    acquisition_cost_ratio: float = 0.0
    brokerage_cost_ratio: float = 0.0


# TODO tidy up and consider refactor and seperate processes
class AggregateFeatures:
    def __init__(self, subject_contract: RIContract, assumptions_inputs: tuple) -> None:
        self._subject_contract = subject_contract
        self._assumptions_inputs = assumptions_inputs

    def create_simulation(self) -> "Simulation":
        from .simulation_engine import Simulation

        return Simulation(...)

    def run_simulation(self, simulation: "Simulation"):
        return None

    def model_output(self):
        return
