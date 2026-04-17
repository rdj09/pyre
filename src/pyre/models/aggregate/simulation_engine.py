"""DFA (Dynamic Financial Analysis) simulation engine for reinsurance pricing.

The Simulation class runs a Monte Carlo model that:
1. Draws aggregate losses from fitted frequency/severity distributions.
2. Applies reinsurance contract layer terms.
3. Computes loss cost, required capital, and required premium per layer.

No external dependencies — uses stdlib random and math only.
"""

import json
import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...treaty.contracts import RIContract

if TYPE_CHECKING:
    from ...models.aggregate.aggregate_features import ModellingAssumptions
    from ...models.experience.frequency_severity import FrequencyFit, SeverityFit


@dataclass
class SimulationResults:
    """Output of a completed Simulation run.

    Attributes:
        loss_cost_by_layer: Mean ceded loss per layer.
        required_capital_by_layer: VaR/TVaR capital per layer.
        required_premium_by_layer: Required premium per layer.
        required_premium_programme: Total required premium across all layers.
        aggregate_loss_distribution: Per-layer sorted simulated aggregate losses.
        n_simulations: Number of Monte Carlo trials run.
        assumptions: The financial assumptions used.
    """
    loss_cost_by_layer: dict[int, float]
    required_capital_by_layer: dict[int, float]
    required_premium_by_layer: dict[int, float]
    required_premium_programme: float
    aggregate_loss_distribution: dict[int, list[float]]
    n_simulations: int
    assumptions: "ModellingAssumptions"


def _sample_lognormal(mu: float, sigma: float, rng: random.Random) -> float:
    """Draw one sample from a lognormal distribution."""
    return math.exp(rng.gauss(mu, sigma))


def _sample_pareto(alpha: float, x_m: float, rng: random.Random) -> float:
    """Draw one sample from a single-parameter Pareto distribution."""
    u = rng.random()
    if u >= 1.0:
        u = 1.0 - 1e-15
    return x_m / ((1.0 - u) ** (1.0 / alpha))


def _sample_poisson(lambda_: float, rng: random.Random) -> int:
    """Draw one sample from a Poisson distribution using Knuth's algorithm."""
    L = math.exp(-lambda_)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1


def _sample_negative_binomial(r: float, p: float, rng: random.Random) -> int:
    """Draw one sample from a Negative Binomial by gamma-Poisson mixture."""
    lambda_ = rng.gammavariate(r, (1.0 - p) / p)
    return _sample_poisson(lambda_, rng)


def _tvar(sorted_losses: list[float], confidence: float) -> float:
    """Tail Value at Risk (Expected Shortfall) at given confidence level."""
    n = len(sorted_losses)
    threshold_idx = int(math.ceil(confidence * n))
    tail = sorted_losses[threshold_idx:]
    if not tail:
        return sorted_losses[-1]
    return sum(tail) / len(tail)


def _var(sorted_losses: list[float], confidence: float) -> float:
    """Value at Risk at given confidence level."""
    n = len(sorted_losses)
    idx = min(int(math.ceil(confidence * n)), n - 1)
    return sorted_losses[idx]


class Simulation:
    """Monte Carlo DFA pricing simulation.

    Args:
        frequency_fit: Fitted frequency distribution.
        severity_fit: Fitted severity distribution.
        ri_contract: Reinsurance contract defining layers.
        assumptions: Financial assumptions (CoC, yield, tax, etc.).
        n_simulations: Number of trials. Defaults to 10,000.
        random_seed: Seed for reproducibility. Defaults to None.
        retrocession_contract: Optional nested retrocession contract.
    """

    def __init__(
        self,
        frequency_fit: "FrequencyFit",
        severity_fit: "SeverityFit",
        ri_contract: RIContract,
        assumptions: "ModellingAssumptions",
        n_simulations: int = 10_000,
        random_seed: int | None = None,
        retrocession_contract: RIContract | None = None,
    ) -> None:
        self._frequency_fit = frequency_fit
        self._severity_fit = severity_fit
        self._ri_contract = ri_contract
        self._assumptions = assumptions
        self._n_simulations = n_simulations
        self._rng = random.Random(random_seed)
        self._retrocession_contract = retrocession_contract

        self._aggregate_losses: dict[int, list[float]] = {}
        self._ran = False

    def _assert_ran(self) -> None:
        if not self._ran:
            raise RuntimeError("Call run() before accessing results.")

    def run(self) -> None:
        """Execute the Monte Carlo simulation."""
        freq_params = self._frequency_fit.fit()
        sev_params = self._severity_fit.fit()

        if "poisson" in freq_params:
            lambda_ = freq_params["poisson"]["lambda_"]
            freq_dist = "poisson"
        elif "negative_binomial" in freq_params:
            freq_dist = "negative_binomial"
        else:
            raise ValueError("No supported frequency distribution fitted.")

        if "lognormal" in sev_params:
            sev_dist = "lognormal"
            mu = sev_params["lognormal"]["mu"]
            sigma = sev_params["lognormal"]["sigma"]
        elif "pareto" in sev_params:
            sev_dist = "pareto"
            alpha = sev_params["pareto"]["alpha"]
            x_m = sev_params["pareto"]["x_m"]
        else:
            raise ValueError("No supported severity distribution fitted.")

        layer_ids = [layer.layer_id for layer in self._ri_contract.layers]
        raw: dict[int, list[float]] = {lid: [] for lid in layer_ids}

        for _ in range(self._n_simulations):
            if freq_dist == "poisson":
                n_claims = _sample_poisson(lambda_, self._rng)
            else:
                nb = freq_params["negative_binomial"]
                n_claims = _sample_negative_binomial(nb["r"], nb["p"], self._rng)

            per_layer_aggregate: dict[int, float] = {lid: 0.0 for lid in layer_ids}
            for _ in range(n_claims):
                if sev_dist == "lognormal":
                    gross = _sample_lognormal(mu, sigma, self._rng)
                else:
                    gross = _sample_pareto(alpha, x_m, self._rng)  # type: ignore[possibly-undefined]

                for layer in self._ri_contract.layers:
                    try:
                        ceded = layer.loss_to_layer_fn(gross)
                    except NotImplementedError:
                        ceded = 0.0
                    per_layer_aggregate[layer.layer_id] += ceded

            for layer in self._ri_contract.layers:
                agg = per_layer_aggregate[layer.layer_id]
                if layer.aggregate_attachment > 0:
                    agg = max(agg - layer.aggregate_attachment, 0.0)
                if layer.aggregate_limit < float("inf"):
                    agg = min(agg, layer.aggregate_limit)
                raw[layer.layer_id].append(agg)

        self._aggregate_losses = {lid: sorted(losses) for lid, losses in raw.items()}
        self._ran = True

    def loss_cost(self) -> dict[int, float]:
        """Mean ceded aggregate loss per layer across all simulations."""
        self._assert_ran()
        return {
            lid: sum(losses) / len(losses) if losses else 0.0
            for lid, losses in self._aggregate_losses.items()
        }

    def required_capital(self) -> dict[int, float]:
        """Risk capital per layer using TVaR or VaR at the configured confidence level."""
        self._assert_ran()
        a = self._assumptions
        result: dict[int, float] = {}
        for lid, losses in self._aggregate_losses.items():
            if a.use_tvar:
                result[lid] = _tvar(losses, a.capital_confidence_level)
            else:
                result[lid] = _var(losses, a.capital_confidence_level)
        return result

    def cashflows(self) -> dict[int, dict[str, float]]:
        """Premium inflow and expected claim outflow per layer."""
        self._assert_ran()
        lc = self.loss_cost()
        result: dict[int, dict[str, float]] = {}
        for layer in self._ri_contract.layers:
            result[layer.layer_id] = {
                "premium": layer.signed_line_premium,
                "claims": lc[layer.layer_id],
            }
        return result

    def investment_return(self) -> dict[int, float]:
        """Present value of investment return on premium float per layer."""
        self._assert_ran()
        cf = self.cashflows()
        y = self._assumptions.investment_yield
        return {lid: cf[lid]["premium"] * y for lid in cf}

    def profit_commission(
        self,
        profit_commission_rate: float = 0.0,
        loss_ratio_threshold: float = 0.6,
    ) -> dict[int, float]:
        """Sliding scale profit commission per layer."""
        self._assert_ran()
        lc = self.loss_cost()
        result: dict[int, float] = {}
        for layer in self._ri_contract.layers:
            premium = layer.signed_line_premium
            if premium == 0:
                result[layer.layer_id] = 0.0
                continue
            actual_lr = lc[layer.layer_id] / premium
            pc = max(0.0, (loss_ratio_threshold - actual_lr) * profit_commission_rate * premium)
            result[layer.layer_id] = pc
        return result

    def retrocession_cost(self) -> dict[int, float]:
        """Net retrocession cost per layer."""
        if self._retrocession_contract is None:
            return {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        retro_premium = sum(
            rl.signed_line_premium for rl in self._retrocession_contract.layers
        )
        self._assert_ran()
        lc = self.loss_cost()
        total_lc = sum(lc.values())
        result: dict[int, float] = {}
        for layer in self._ri_contract.layers:
            share = lc[layer.layer_id] / total_lc if total_lc > 0 else 1.0 / len(self._ri_contract.layers)
            result[layer.layer_id] = retro_premium * share
        return result

    def retrocession_benefits(self) -> dict[int, float]:
        """Expected ceded loss recovered from retrocession per subject layer."""
        if self._retrocession_contract is None:
            return {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        self._assert_ran()
        retro_layer_ids = [rl.layer_id for rl in self._retrocession_contract.layers]
        subject_layer_ids = [layer.layer_id for layer in self._ri_contract.layers]

        retro_recoveries: dict[int, list[float]] = {rid: [] for rid in retro_layer_ids}
        for lid in subject_layer_ids:
            losses = self._aggregate_losses.get(lid, [])
            for gross_agg in losses:
                for rl in self._retrocession_contract.layers:
                    try:
                        ceded = rl.loss_to_layer_fn(gross_agg)
                    except NotImplementedError:
                        ceded = 0.0
                    retro_recoveries[rl.layer_id].append(ceded)

        mean_retro = sum(
            sum(v) / len(v) if v else 0.0
            for v in retro_recoveries.values()
        )

        lc = self.loss_cost()
        total_lc = sum(lc.values())
        result: dict[int, float] = {}
        for layer in self._ri_contract.layers:
            share = lc[layer.layer_id] / total_lc if total_lc > 0 else 1.0 / len(self._ri_contract.layers)
            result[layer.layer_id] = mean_retro * share
        return result

    def required_premium_layer(self) -> dict[int, float]:
        """Required premium per layer using the DFA pricing formula."""
        self._assert_ran()
        a = self._assumptions
        lc = self.loss_cost()
        rc = self.required_capital()
        ir = self.investment_return()
        retro_cost = self.retrocession_cost()
        retro_ben = self.retrocession_benefits()

        expense_ratio = a.acquisition_cost_ratio + a.brokerage_cost_ratio
        loadings_multiplier = 1.0 / (1.0 - expense_ratio) if expense_ratio < 1.0 else 1.0

        result: dict[int, float] = {}
        for layer in self._ri_contract.layers:
            lid = layer.layer_id
            net_tech_cost = (
                lc[lid]
                + a.cost_of_capital * rc[lid]
                - ir[lid]
                + retro_cost[lid]
                - retro_ben[lid]
            )
            result[lid] = net_tech_cost * loadings_multiplier

        return result

    def required_premium_programme(self) -> float:
        """Total required premium across all layers."""
        self._assert_ran()
        return sum(self.required_premium_layer().values())

    def output(self) -> SimulationResults:
        """Return a SimulationResults dataclass with all computed metrics."""
        self._assert_ran()
        return SimulationResults(
            loss_cost_by_layer=self.loss_cost(),
            required_capital_by_layer=self.required_capital(),
            required_premium_by_layer=self.required_premium_layer(),
            required_premium_programme=self.required_premium_programme(),
            aggregate_loss_distribution=self._aggregate_losses,
            n_simulations=self._n_simulations,
            assumptions=self._assumptions,
        )

    def save(self, path: str) -> None:
        """Serialise SimulationResults to a JSON file."""
        results = self.output()
        data = {
            "loss_cost_by_layer": {str(k): v for k, v in results.loss_cost_by_layer.items()},
            "required_capital_by_layer": {str(k): v for k, v in results.required_capital_by_layer.items()},
            "required_premium_by_layer": {str(k): v for k, v in results.required_premium_by_layer.items()},
            "required_premium_programme": results.required_premium_programme,
            "n_simulations": results.n_simulations,
            "assumptions": {
                "cost_of_capital": results.assumptions.cost_of_capital,
                "required_rate_of_return": results.assumptions.required_rate_of_return,
                "capital_confidence_level": results.assumptions.capital_confidence_level,
                "use_tvar": results.assumptions.use_tvar,
                "investment_yield": results.assumptions.investment_yield,
                "tax_rate": results.assumptions.tax_rate,
                "acquisition_cost_ratio": results.assumptions.acquisition_cost_ratio,
                "brokerage_cost_ratio": results.assumptions.brokerage_cost_ratio,
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
