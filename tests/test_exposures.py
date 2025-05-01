import unittest
from datetime import date

from src.pyre.exposures.exposures import (
    ExposureBasis,
    ExposureMetaData,
    ExposureValues,
    Exposure,
    AggregateExposures,
)

class TestExposureMetaData(unittest.TestCase):
    def setUp(self):
        self.meta_data = ExposureMetaData(
            exposure_id="EXP001",
            exposure_name="Test Exposure",
            exposure_period_start=date(2023, 1, 1),
            exposure_period_end=date(2023, 12, 31),
            currency="USD",
            aggregate=False,
        )

    def test_exposure_term_length_days(self):
        self.assertEqual(self.meta_data.exposure_term_length_days, 364)


class TestExposureValues(unittest.TestCase):
    def setUp(self):
        self.values = ExposureValues(
            exposure_value=100000.0,
            attachment_point=5000.0,
            limit=50000.0,
        )

    def test_exposure_values(self):
        self.assertEqual(self.values.exposure_value, 100000.0)
        self.assertEqual(self.values.attachment_point, 5000.0)
        self.assertEqual(self.values.limit, 50000.0)


class TestExposure(unittest.TestCase):
    def setUp(self):
        self.meta_data = ExposureMetaData(
            exposure_id="EXP001",
            exposure_name="Test Exposure",
            exposure_period_start=date(2024, 1, 1),
            exposure_period_end=date(2024, 12, 31),
            currency="USD",
            aggregate=False,
        )
        self.values = ExposureValues(
            exposure_value=100000.0,
            attachment_point=5000.0,
            limit=50000.0,
        )
        self.exposure = Exposure(self.meta_data, self.values)

    def test_modelling_year(self):
        self.assertEqual(self.exposure.modelling_year, 2024)

    def test_term_length_days(self):
        self.assertEqual(self.exposure._exposure_meta.exposure_term_length_days, 365)

    def test_earned_pct(self):
        analysis_date = date(2024, 6, 30)
        self.assertAlmostEqual(self.exposure._earned_pct(analysis_date), 0.5)

    def test_earned_exposure_value(self):
        analysis_date = date(2024, 6, 30)
        self.assertAlmostEqual(self.exposure.earned_exposure_value(analysis_date), 50000.0)


class TestAggregateExposures(unittest.TestCase):
    def setUp(self):
        self.aggregate_exposures = AggregateExposures()

    def test_aggregate_exposures_initialization(self):
        self.assertIsInstance(self.aggregate_exposures, AggregateExposures)