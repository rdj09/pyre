import unittest
from unittest.mock import MagicMock
from pyre.models.Experience.resampling import resampling
from pyre.claims.claims import Claims


class TestResamplingInit(unittest.TestCase):
    def test_init_uses_claims_argument_trended_claims(self):
        fake_claims = Claims([])
        mock_data = MagicMock()
        mock_data.trended_claims = fake_claims
        r = resampling(mock_data)
        self.assertIs(r._claims, fake_claims)
