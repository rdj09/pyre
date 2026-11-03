import random
import unittest
from math import exp
from unittest.mock import PropertyMock, patch

from pyre.enums import FrequencyDistribution, SeverityDistribution
from pyre.models.Experience.frequency_severity import FitResult, FrequencyFit, SeverityFit

# Step 5 (golden-value test) note: *Loss Models* (Klugman, Panjer & Willmot)
# own worked MLE example for the single-parameter Pareto could not be
# independently verified. Web search surfaced a 5-observation Pareto MLE
# dataset (521, 658, 702, 819, 1217; theta=500 -> alpha_hat ~= 2.453), but
# that dataset traces to an SOA Exam C/4 (May 2000, Q21) problem reproduced
# in a different, open-source textbook ("Loss Data Analytics", Ch. 17
# Appendix C) -- not to a confirmed worked example inside Loss Models itself.
# Loss Models' own chapter numbering for MLE/method-of-moments also differs
# between editions (Ch. 11 in the 5th ed. vs. the Ch. 13 cited in this
# module's fit() docstring for the 4th ed.), which could not be
# cross-checked against the actual book text. Per the task brief, fabricating
# input data to reproduce a remembered output is not acceptable, so no
# textbook golden-value test is included here -- the tests below are
# regression tests against known synthetic parameters only.


def _patched_fit(distributions, data):
    """Build a SeverityFit whose `_individual_projected_claims` returns `data`."""
    fit = SeverityFit(distributions=distributions, data=None, ibner_dev_pattern={})
    return fit


class TestSeverityFitNonGroundUp(unittest.TestCase):
    def test_non_ground_up_fit_raises_not_implemented_error(self):
        fit = SeverityFit(distributions=[], data=None, ibner_dev_pattern={}, ground_up=False)
        with self.assertRaises(NotImplementedError):
            fit._individual_projected_claims


class TestSeverityFitLognormal(unittest.TestCase):
    def test_fit_lognormal_recovers_known_parameters(self):
        # Synthetic data drawn from a known lognormal (mu=8.0, sigma=0.5):
        # X = exp(N(mu, sigma)). With n=20,000 and a fixed seed, the
        # method-of-moments estimates should land within +/-0.03 of the true
        # mu and sigma (documented tolerance for this regression test).
        rng = random.Random(42)
        mu_true, sigma_true = 8.0, 0.5
        data = [exp(rng.normalvariate(mu_true, sigma_true)) for _ in range(20_000)]

        fit = _patched_fit([SeverityDistribution.LOGNORMAL], data)
        with patch.object(
            SeverityFit,
            "_individual_projected_claims",
            new_callable=PropertyMock,
            return_value=data,
        ):
            results = fit.fit()

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIsInstance(result, FitResult)
        self.assertEqual(result.distribution, SeverityDistribution.LOGNORMAL)
        self.assertAlmostEqual(result.parameters["mu"], mu_true, delta=0.03)
        self.assertAlmostEqual(result.parameters["sigma"], sigma_true, delta=0.03)
        self.assertIsInstance(result.log_likelihood, float)
        self.assertIsInstance(result.aic, float)


class TestSeverityFitPareto(unittest.TestCase):
    def test_fit_pareto_recovers_known_parameters(self):
        # Synthetic data drawn from a known single-parameter Pareto
        # (alpha=2.5, x_m=1000) via inverse-CDF sampling:
        # X = x_m / (1 - U) ** (1 / alpha), U ~ Uniform(0, 1). With n=20,000
        # and a fixed seed, the MLE alpha should land within +/-0.1 of the
        # true alpha, and the sample minimum (the MLE of x_m) within +/-5 of
        # the true x_m (documented tolerances for this regression test).
        rng = random.Random(7)
        alpha_true, x_m_true = 2.5, 1000.0
        data = [x_m_true / (1 - rng.random()) ** (1 / alpha_true) for _ in range(20_000)]

        fit = _patched_fit([SeverityDistribution.PARETO], data)
        with patch.object(
            SeverityFit,
            "_individual_projected_claims",
            new_callable=PropertyMock,
            return_value=data,
        ):
            results = fit.fit()

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIsInstance(result, FitResult)
        self.assertEqual(result.distribution, SeverityDistribution.PARETO)
        self.assertAlmostEqual(result.parameters["alpha"], alpha_true, delta=0.1)
        self.assertAlmostEqual(result.parameters["x_m"], x_m_true, delta=5.0)
        self.assertIsInstance(result.log_likelihood, float)
        self.assertIsInstance(result.aic, float)


class TestSeverityFitUnsupportedDistribution(unittest.TestCase):
    def test_fit_raises_not_implemented_for_other_distribution(self):
        fit = _patched_fit([SeverityDistribution.OTHER], [1.0, 2.0, 3.0])
        with patch.object(
            SeverityFit,
            "_individual_projected_claims",
            new_callable=PropertyMock,
            return_value=[1.0, 2.0, 3.0],
        ):
            with self.assertRaises(NotImplementedError):
                fit.fit()


# FrequencyFit golden-value note: unlike SeverityFit's lognormal/Pareto fits,
# there is no textbook worked example to regress against here either. The
# Negative Binomial method-of-moments estimator (p_hat = m/v, r_hat =
# m**2/(v-m), derived in frequency_severity.py's _fit_negative_binomial
# docstring) is closed-form and simple enough that no golden value is
# expected or required (per the task brief) -- the tests below are
# regression-only, checking that fitting synthetic data generated from known
# parameters recovers those parameters within a documented tolerance.


def _poisson_rvs(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm: draw a single Poisson(lam) variate from `rng`."""
    l_threshold = exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= l_threshold:
            return k - 1


def _negative_binomial_rvs(rng: random.Random, r: float, p: float) -> int:
    """Draw a single NegBin(r, p) variate via the Gamma-Poisson mixture:
    Lambda ~ Gamma(shape=r, scale=(1-p)/p), N | Lambda ~ Poisson(Lambda).

    This mixture has mean = r*(1-p)/p and variance = r*(1-p)/p**2 -- the
    same actuarial parameterization used by `_fit_negative_binomial`.
    """
    scale = (1 - p) / p
    lam = rng.gammavariate(r, scale)
    return _poisson_rvs(rng, lam)


class TestFrequencyFitPoisson(unittest.TestCase):
    def test_fit_poisson_recovers_known_lambda(self):
        # Synthetic data drawn from a known Poisson(lambda=3.5) via Knuth's
        # algorithm. With n=20,000 and a fixed seed, the MLE lambda should
        # land within +/-0.1 of the true lambda (documented tolerance for
        # this regression test).
        rng = random.Random(123)
        lambda_true = 3.5
        data = [_poisson_rvs(rng, lambda_true) for _ in range(20_000)]

        fit = FrequencyFit(distributions=[FrequencyDistribution.POISSON], claim_counts=data)
        results = fit.fit()

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIsInstance(result, FitResult)
        self.assertEqual(result.distribution, FrequencyDistribution.POISSON)
        self.assertAlmostEqual(result.parameters["lambda"], lambda_true, delta=0.1)
        self.assertIsInstance(result.log_likelihood, float)
        self.assertIsInstance(result.aic, float)


class TestFrequencyFitNegativeBinomial(unittest.TestCase):
    def test_fit_negative_binomial_recovers_known_parameters(self):
        # Synthetic data drawn from a known Negative Binomial (r=4.0, p=0.4)
        # via the Gamma-Poisson mixture (see `_negative_binomial_rvs`), which
        # is overdispersed (mean=6.0, variance=15.0). With n=20,000 and a
        # fixed seed, the method-of-moments p_hat should land within +/-0.05
        # of the true p, and r_hat within +/-0.3 of the true r (documented
        # tolerances for this regression test -- r_hat has higher sampling
        # variance since it depends on the difference v - m).
        rng = random.Random(99)
        r_true, p_true = 4.0, 0.4
        data = [_negative_binomial_rvs(rng, r_true, p_true) for _ in range(20_000)]

        fit = FrequencyFit(
            distributions=[FrequencyDistribution.NEGATIVE_BINOMIAL], claim_counts=data
        )
        results = fit.fit()

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIsInstance(result, FitResult)
        self.assertEqual(result.distribution, FrequencyDistribution.NEGATIVE_BINOMIAL)
        self.assertAlmostEqual(result.parameters["p"], p_true, delta=0.05)
        self.assertAlmostEqual(result.parameters["r"], r_true, delta=0.3)
        self.assertIsInstance(result.log_likelihood, float)
        self.assertIsInstance(result.aic, float)

    def test_fit_negative_binomial_raises_value_error_when_not_overdispersed(self):
        # Equal counts give sample variance 0, which is <= the sample mean
        # for any positive mean -- not overdispersed, so the method of
        # moments estimator is undefined (p_hat would be >= 1).
        data = [5] * 10
        fit = FrequencyFit(
            distributions=[FrequencyDistribution.NEGATIVE_BINOMIAL], claim_counts=data
        )
        with self.assertRaises(ValueError):
            fit.fit()


class TestFrequencyFitUnsupportedDistribution(unittest.TestCase):
    def test_fit_raises_not_implemented_for_other_distribution(self):
        fit = FrequencyFit(distributions=[FrequencyDistribution.OTHER], claim_counts=[1, 2, 3])
        with self.assertRaises(NotImplementedError):
            fit.fit()
