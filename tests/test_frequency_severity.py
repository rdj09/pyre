import unittest
from pyre.models.Experience.frequency_severity import SeverityFit


class TestSeverityFitNonGroundUp(unittest.TestCase):
    def test_non_ground_up_fit_raises_not_implemented_error(self):
        fit = SeverityFit(distributions=[], data=None, ibner_dev_pattern={}, ground_up=False)
        with self.assertRaises(NotImplementedError):
            fit._individual_projected_claims
