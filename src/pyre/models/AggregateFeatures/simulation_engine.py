import dataclasses
import json
import math
import random
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

from ...enums import FrequencyDistribution, SeverityDistribution
from ...treaty.contracts import RIContract
from ..Experience.frequency_severity import FitResult
from .aggregate_features import ModellingAssumptions


@dataclass
class SimulationResults:
    """Snapshot of all per-layer and programme-level output of a
    :class:`Simulation`, as produced by :meth:`Simulation.output` and
    serialised to JSON by :meth:`Simulation.save`.
    """

    loss_cost: Dict[int, float]
    required_capital: Dict[int, float]
    required_premium_layer: Dict[int, float]
    required_premium_programme: float
    investment_return: Dict[int, float]
    retrocession_benefits: Dict[int, float]
    retrocession_cost: Dict[int, float]
    profit_commission: Dict[int, float]


def _sample_poisson(rng: random.Random, lam: float) -> int:
    """Draw a single Poisson(lam) variate via Knuth's algorithm.

    Stdlib's ``random`` module has no built-in Poisson sampler, so this
    implements the standard inversion-by-simulation method: the number of
    unit-rate exponential waiting times that fit into an interval of
    length ``lam`` is Poisson(lam)-distributed. Multiplying successive
    uniform(0,1) draws is equivalent (via their logs summing to the
    exponential waiting times) to this and avoids computing logs directly.
    """
    l_bound = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= l_bound:
            return k - 1


def _sample_negative_binomial(rng: random.Random, r: float, p: float) -> int:
    """Draw a single Negative Binomial(r, p) variate via the standard
    Gamma-Poisson mixture: if ``lam ~ Gamma(r, (1-p)/p)`` and
    ``N | lam ~ Poisson(lam)``, then marginally ``N ~ NegBin(r, p)``. This
    is a standard probabilistic identity (see e.g. Klugman, Panjer &
    Willmot, *Loss Models*, 4th ed., Ch. 6) and lets Negative Binomial
    variates be drawn from stdlib's ``gammavariate`` plus the Poisson
    sampler above, without a dedicated RNG primitive.
    """
    lam = rng.gammavariate(r, (1 - p) / p)
    return _sample_poisson(rng, lam)


class Simulation:
    """Monte Carlo simulation of a reinsurance contract's aggregate loss
    experience, given a fitted frequency distribution and a fitted
    severity distribution.

    For each of ``n_simulations`` simulated years, a claim count is drawn
    from ``frequency_fit``, that many individual claim severities are
    drawn from ``severity_fit``, and each severity is passed through every
    layer's :meth:`RILayer.loss_to_layer_fn` and summed to give that
    simulated year's aggregate ceded loss for the layer. The resulting
    per-layer distributions of simulated aggregate ceded loss back
    :meth:`loss_cost` and :meth:`required_capital`.
    """

    def __init__(
        self,
        frequency_fit: FitResult,
        severity_fit: FitResult,
        ri_contract: RIContract,
        assumptions: ModellingAssumptions,
        n_simulations: int = 10_000,
        random_seed: Optional[int] = None,
        retrocession_contract: Optional[RIContract] = None,
    ) -> None:
        self.frequency_fit = frequency_fit
        self.severity_fit = severity_fit
        self.ri_contract = ri_contract
        self.assumptions = assumptions
        self.n_simulations = n_simulations
        self.random_seed = random_seed
        self.retrocession_contract = retrocession_contract
        self._ceded_losses: Dict[int, List[float]] = {}

    def _sample_frequency(self, rng: random.Random) -> int:
        distribution = self.frequency_fit.distribution
        parameters = self.frequency_fit.parameters
        if distribution == FrequencyDistribution.POISSON:
            return _sample_poisson(rng, parameters["lambda"])
        if distribution == FrequencyDistribution.NEGATIVE_BINOMIAL:
            return _sample_negative_binomial(rng, parameters["r"], parameters["p"])
        raise NotImplementedError(
            f"Sampling for frequency distribution {distribution} has not been implemented yet"
        )

    def _sample_severity(self, rng: random.Random) -> float:
        distribution = self.severity_fit.distribution
        parameters = self.severity_fit.parameters
        if distribution == SeverityDistribution.LOGNORMAL:
            return rng.lognormvariate(parameters["mu"], parameters["sigma"])
        if distribution == SeverityDistribution.PARETO:
            return parameters["x_m"] * rng.paretovariate(parameters["alpha"])
        raise NotImplementedError(
            f"Sampling for severity distribution {distribution} has not been implemented yet"
        )

    def run(self) -> None:
        """Run the Monte Carlo simulation, populating ``self._ceded_losses``
        (a per-layer list of simulated aggregate ceded loss, one entry per
        simulated year) for use by :meth:`loss_cost` and
        :meth:`required_capital`.
        """
        rng = random.Random(self.random_seed) if self.random_seed is not None else random
        self._ceded_losses = {layer.layer_id: [] for layer in self.ri_contract.layers}
        for _ in range(self.n_simulations):
            claim_count = self._sample_frequency(rng)
            severities = [self._sample_severity(rng) for _ in range(claim_count)]
            sim_ceded_by_layer = {layer.layer_id: 0.0 for layer in self.ri_contract.layers}
            for severity in severities:
                for layer in self.ri_contract.layers:
                    sim_ceded_by_layer[layer.layer_id] += layer.loss_to_layer_fn(severity)
            for layer_id, total in sim_ceded_by_layer.items():
                self._ceded_losses[layer_id].append(total)

    def loss_cost(self) -> Dict[int, float]:
        """Mean simulated aggregate ceded loss per layer, across all
        simulated years."""
        return {
            layer_id: statistics.mean(losses) for layer_id, losses in self._ceded_losses.items()
        }

    def required_capital(self) -> Dict[int, float]:
        """Risk-adjusted capital required per layer, computed as the
        *unexpected* loss -- the tail statistic (VaR or TVaR, per
        ``assumptions.use_tvar``) of the simulated ceded-loss distribution
        in excess of that distribution's mean -- floored at 0.0.

        This "capital held against losses beyond what's already priced
        for in the loss cost" framing follows Butsic, R.P. (1999),
        "Capital Allocation for Property-Liability Insurers: A
        Catastrophe Reinsurance Application," CAS Forum. Returning the
        raw VaR/TVaR itself (rather than netting off the mean) would
        double-count the expected loss once a required-premium
        calculation adds ``loss_cost + cost_of_capital * required_capital``.

        The ``capital_confidence_level`` default of 0.995 used by
        :class:`ModellingAssumptions` is a commonly used convention in
        practice (e.g. Solvency II's 1-in-200 standard) rather than a
        value mandated by Butsic or the DFA Handbook.

        VaR is the empirical ``capital_confidence_level``-th percentile of
        the sorted simulated ceded losses (index
        ``ceil(capital_confidence_level * n) - 1``, clamped to the sample).
        TVaR is the mean of all simulated ceded losses at or above that
        VaR (expected shortfall / conditional tail expectation).
        """
        result: Dict[int, float] = {}
        for layer_id, losses in self._ceded_losses.items():
            sorted_losses = sorted(losses)
            n = len(sorted_losses)
            idx = min(max(math.ceil(self.assumptions.capital_confidence_level * n) - 1, 0), n - 1)
            var = sorted_losses[idx]
            if self.assumptions.use_tvar:
                tail_measure = statistics.mean([x for x in sorted_losses if x >= var])
            else:
                tail_measure = var
            result[layer_id] = max(tail_measure - statistics.mean(losses), 0.0)
        return result

    def investment_return(self) -> Dict[int, float]:
        """Investment income earned by holding the expected loss cost for
        ``assumptions.mean_payment_duration_years`` before payment, at
        ``assumptions.investment_yield``. Cites Clark, D.R. (1996/2014),
        Basics of Reinsurance Pricing, CAS Study Note, Section B
        (investment income treatment) -- same citation already used for
        SURPLUS_SHARE elsewhere in this repo.
        """
        loss_cost = self.loss_cost()
        factor = (
            1 + self.assumptions.investment_yield
        ) ** self.assumptions.mean_payment_duration_years - 1
        return {layer_id: lc * factor for layer_id, lc in loss_cost.items()}

    def cashflows(self) -> Dict[int, Dict[str, float]]:
        """Purely informational/documentary summary of the premium inflow
        and (mean-duration) claims outflow timing per layer -- not
        load-bearing for :meth:`required_premium_layer`, which uses
        :meth:`investment_return` directly.
        """
        loss_cost = self.loss_cost()
        return {
            layer_id: {
                "premium_inflow_t0": lc,
                "claims_outflow_mean_duration_years": self.assumptions.mean_payment_duration_years,
            }
            for layer_id, lc in loss_cost.items()
        }

    def profit_commission(self) -> Dict[int, float]:
        """Simplified: a configurable rate
        (``assumptions.profit_commission_rate``, default 0.0) applied to
        ``loss_cost``, approximating an expected profit-share cost without
        the circularity of computing it against the premium this method's
        own output feeds into. No source mandates a specific rate.
        """
        loss_cost = self.loss_cost()
        return {
            layer_id: self.assumptions.profit_commission_rate * lc
            for layer_id, lc in loss_cost.items()
        }

    def retrocession_benefits(self) -> Dict[int, float]:
        """Mean amount recovered from the retrocession program per primary
        layer, for primary layers with a same-``layer_id`` counterpart in
        ``retrocession_contract``.

        Convention (a documented simplification -- no source pins a
        number): a retrocession layer protects the primary layer with the
        SAME ``layer_id``. The caller is responsible for constructing
        ``retrocession_contract`` with layers whose ``layer_id``s match the
        primary layers they're meant to protect.

        Simplified convention: retro applies to each year's AGGREGATE
        ceded loss for that primary layer (not per-claim), matching how a
        real aggregate/annual retro program would sit over a primary
        treaty's ceded result.
        """
        result = {layer_id: 0.0 for layer_id in self._ceded_losses}
        if self.retrocession_contract is None:
            return result
        retro_layers_by_id = {layer.layer_id: layer for layer in self.retrocession_contract.layers}
        for layer_id, yearly_ceded in self._ceded_losses.items():
            retro_layer = retro_layers_by_id.get(layer_id)
            if retro_layer is None:
                continue
            recoveries = [retro_layer.loss_to_layer_fn(amount) for amount in yearly_ceded]
            result[layer_id] = statistics.mean(recoveries)
        return result

    def retrocession_cost(self) -> Dict[int, float]:
        """Simplified expected cost of the retrocession program: a
        configurable loading (``assumptions.retrocession_premium_loading``,
        default 0.0 -- no source mandates a specific number) applied to
        expected recoveries.
        """
        benefits = self.retrocession_benefits()
        return {
            layer_id: self.assumptions.retrocession_premium_loading * benefit
            for layer_id, benefit in benefits.items()
        }

    def required_premium_layer(self, layer_id: int) -> float:
        """Required premium for one layer: loss cost plus a capital
        charge, net of investment income and retrocession, grossed up for
        premium-based expense ratios (acquisition + brokerage) per the
        standard CAS expense-loading treatment (Werner & Modlin, Basic
        Ratemaking, 5th ed., CAS). ``profit_commission`` is treated as an
        additional premium-based cost here too, folded into the same
        grossing-up (it's computed off ``loss_cost``, not premium,
        avoiding circularity -- see :meth:`profit_commission`).

        This corrects the naive treatment of adding
        ``acquisition_cost_ratio``/``brokerage_cost_ratio`` as if they were
        dollar amounts: since they are ratios OF premium, the standard
        "grossing up for expenses" treatment is
        ``premium = everything_else / (1 - expense_ratio)``.
        """
        loss_cost = self.loss_cost()[layer_id]
        capital_charge = self.assumptions.cost_of_capital * self.required_capital()[layer_id]
        investment_credit = self.investment_return()[layer_id]
        net_retro = self.retrocession_cost()[layer_id] - self.retrocession_benefits()[layer_id]
        profit_comm = self.profit_commission()[layer_id]

        numerator = loss_cost + capital_charge - investment_credit + net_retro + profit_comm
        expense_ratio = (
            self.assumptions.acquisition_cost_ratio + self.assumptions.brokerage_cost_ratio
        )
        if expense_ratio >= 1.0:
            raise ValueError(
                f"acquisition_cost_ratio + brokerage_cost_ratio ({expense_ratio}) must be < 1.0"
            )
        return numerator / (1.0 - expense_ratio)

    def required_premium_programme(self) -> float:
        """Sum of :meth:`required_premium_layer` across all layers."""
        return sum(self.required_premium_layer(layer_id) for layer_id in self._ceded_losses)

    def output(self) -> SimulationResults:
        """Snapshot all per-layer and programme-level output into a
        :class:`SimulationResults` dataclass."""
        return SimulationResults(
            loss_cost=self.loss_cost(),
            required_capital=self.required_capital(),
            required_premium_layer={
                lid: self.required_premium_layer(lid) for lid in self._ceded_losses
            },
            required_premium_programme=self.required_premium_programme(),
            investment_return=self.investment_return(),
            retrocession_benefits=self.retrocession_benefits(),
            retrocession_cost=self.retrocession_cost(),
            profit_commission=self.profit_commission(),
        )

    def save(self, path: str) -> None:
        """Write :meth:`output` to ``path`` as JSON via the stdlib ``json``
        module (no new dependency)."""
        with open(path, "w") as f:
            json.dump(dataclasses.asdict(self.output()), f, indent=2)
