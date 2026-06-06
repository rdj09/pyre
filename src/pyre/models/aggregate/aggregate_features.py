"""Aggregate pricing features and orchestration.

ModellingAssumptions is defined here and imported by simulation_engine.
AggregateFeatures is the top-level orchestrator for a full pricing run.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...models.aggregate.selections import Selections
from ...models.experience.experience_preparer import ExperienceModelData
from ...models.exposure.exposure_rating_cost import ExposureModel

if TYPE_CHECKING:
    from ...models.aggregate.simulation_engine import SimulationResults


@dataclass
class ModellingAssumptions:
    """Financial assumptions for a DFA pricing simulation.

    Attributes:
        cost_of_capital: Required return on risk capital (e.g. 0.08 = 8%).
        required_rate_of_return: Minimum acceptable return on equity.
        capital_confidence_level: Confidence level for VaR/TVaR (default 99.5% = Solvency II).
        use_tvar: If True, use TVaR; if False, use VaR. Defaults to True.
        investment_yield: Annual investment return on float. Defaults to 0.0.
        tax_rate: Combined premium and profit tax rate. Defaults to 0.0.
        acquisition_cost_ratio: Acquisition costs as proportion of premium. Defaults to 0.0.
        brokerage_cost_ratio: Brokerage as proportion of premium. Defaults to 0.0.
    """

    cost_of_capital: float
    required_rate_of_return: float
    capital_confidence_level: float = 0.995
    use_tvar: bool = True
    investment_yield: float = 0.0
    tax_rate: float = 0.0
    acquisition_cost_ratio: float = 0.0
    brokerage_cost_ratio: float = 0.0


class AggregateFeatures:
    """Orchestrates the full pricing workflow: select → simulate → output.

    Args:
        experience_data: Claims and exposures prepared for experience rating.
        exposure_data: Exposure model for exposure rating.
        selections: Credibility-weighting logic.
        assumptions: Financial/capital assumptions for the simulation.
    """

    def __init__(
        self,
        experience_data: ExperienceModelData,
        exposure_data: ExposureModel,
        selections: Selections,
        assumptions: ModellingAssumptions,
    ) -> None:
        self._experience_data = experience_data
        self._exposure_data = exposure_data
        self._selections = selections
        self._assumptions = assumptions

    def run(self, n_simulations: int = 10_000) -> "SimulationResults":
        """Execute the full pricing workflow.

        1. Calculate credibility weights from selections.
        2. Build frequency and severity fits from experience data.
        3. Run Monte Carlo simulation.
        4. Return SimulationResults.

        Args:
            n_simulations: Number of Monte Carlo trials. Defaults to 10,000.

        Returns:
            SimulationResults dataclass with loss distribution and required premiums.
        """
        from ...enums import FrequencyDistribution, SeverityDistribution
        from ...models.aggregate.simulation_engine import Simulation
        from ...models.experience.frequency_severity import FrequencyFit, SeverityFit

        frequency_fit = FrequencyFit(
            distributions=[FrequencyDistribution.POISSON],
            data=self._experience_data,
        )
        severity_fit = SeverityFit(
            distributions=[SeverityDistribution.LOGNORMAL],
            data=self._experience_data,
            ibner_dev_pattern={year: 1.0 for year in self._experience_data.claims.modelling_years},
        )

        simulation = Simulation(
            frequency_fit=frequency_fit,
            severity_fit=severity_fit,
            ri_contract=self._experience_data.ri_contract,
            assumptions=self._assumptions,
            n_simulations=n_simulations,
        )
        simulation.run()
        return simulation.output()
