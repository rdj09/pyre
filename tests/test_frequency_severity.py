import random
import unittest
from math import exp
from unittest.mock import PropertyMock, patch

from pyre.enums import SeverityDistribution
from pyre.models.Experience.frequency_severity import FitResult, SeverityFit

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
