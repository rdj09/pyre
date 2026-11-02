import unittest
from datetime import date
from unittest.mock import MagicMock
from pyre.models.Experience.resampling import resampling
from pyre.claims.claims import Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData


class TestResamplingInit(unittest.TestCase):
    def test_init_uses_claims_argument_trended_claims(self):
        fake_claims = Claims([])
        mock_data = MagicMock()
        mock_data.trended_claims = fake_claims
        r = resampling(mock_data)
        self.assertIs(r._claims, fake_claims)


def _make_claim(claim_id: str) -> Claim:
    meta_data = ClaimsMetaData(
        claim_id=claim_id,
        currency="USD",
        loss_date=date(2020, 1, 1),
    )
    dev_history = ClaimDevelopmentHistory(
        development_months=[12, 24],
        cumulative_dev_paid=[100.0, 150.0],
        cumulative_dev_incurred=[120.0, 150.0],
    )
    return Claim(meta_data, dev_history)


def _mock_data_with_3_claims() -> MagicMock:
    """Build a mock ExperienceModelData whose trended_claims is a Claims
    container of 3 real Claim objects, for use with resampling.resample().
    """
    fake_claims = Claims([_make_claim("c1"), _make_claim("c2"), _make_claim("c3")])
    mock_data = MagicMock()
    mock_data.trended_claims = fake_claims
    return mock_data


class TestResamplingResample(unittest.TestCase):
    """Tests for resampling.resample(n, random_seed).

    No golden (hardcoded) expected output is possible here: resample() draws
    randomly from the claims pool, so the chosen claims themselves are not
    predictable ahead of time. Instead, determinism is verified by fixing
    random_seed and asserting two calls return identical (by identity)
    sequences of Claim objects -- this substitutes for a golden value.
    """

    def test_resample_n_returns_n_claims(self):
        r = resampling(_mock_data_with_3_claims())
        result = r.resample(n=5, random_seed=42)
        self.assertEqual(len(result), 5)
        for claim in result:
            self.assertIsInstance(claim, Claim)

    def test_resample_is_deterministic_with_seed(self):
        r = resampling(_mock_data_with_3_claims())
        first = r.resample(n=10, random_seed=7)
        second = r.resample(n=10, random_seed=7)
        self.assertEqual([id(c) for c in first], [id(c) for c in second])
