import math
import random
import statistics
from typing import Dict, List, Optional

from ...enums import FrequencyDistribution, SeverityDistribution
from ...treaty.contracts import RIContract
from ..Experience.frequency_severity import FitResult
from .aggregate_features import ModellingAssumptions


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

    def output(self) -> None:
        pass

    def save(self) -> None:
        pass

    def profit_commission(self):
        pass

    def cashflows(self):
        # premium and claims
        pass

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
            idx = min(
                max(math.ceil(self.assumptions.capital_confidence_level * n) - 1, 0), n - 1
            )
            var = sorted_losses[idx]
            if self.assumptions.use_tvar:
                tail_measure = statistics.mean([x for x in sorted_losses if x >= var])
            else:
                tail_measure = var
            result[layer_id] = max(tail_measure - statistics.mean(losses), 0.0)
        return result

    def investment_return(self):  # / discounting:
        # pattern and yeild assumptions from all cashflows
        pass

    def tax_rate(self):
        # premium tax rate and proift?
        pass

    def retrocession_cost(self):
        # additioanl costs from risk mitigation techniques
        pass

    def retrocession_benefits(self):
        pass

    def required_premium_layer(self):
        # required_capital = required_capital()
        # investment_return = investment_return()
        # tax_rate = tax_rate()
        # retrocession_cost = retrocession_cost()
        # loss_cost = loss_cost()
        # acquisition_cost = 0.0
        # brokerage_cost = 0.0
        # expenses_other_costs = 0.0
        pass

    def required_premium_programme(self):
        # for x in range(blah):
        #     total += required_premium_layer()
        # return total
        pass
