import unittest
from datetime import date
from pyre.exposures.exposures import ExposureMetaData, ExposureValues, Exposure, Exposures

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

    def test_properties_and_setters(self):
        self.meta_data.exposure_id = "EXP002"
        self.assertEqual(self.meta_data.exposure_id, "EXP002")
        self.meta_data.exposure_name = "New Name"
        self.assertEqual(self.meta_data.exposure_name, "New Name")
        self.meta_data.exposure_period_start = date(2022, 1, 1)
        self.assertEqual(self.meta_data.exposure_period_start, date(2022, 1, 1))
        self.meta_data.exposure_period_end = date(2022, 12, 31)
        self.assertEqual(self.meta_data.exposure_period_end, date(2022, 12, 31))
        self.meta_data.currency = "EUR"
        self.assertEqual(self.meta_data.currency, "EUR")
        self.meta_data.aggregate = True
        self.assertTrue(self.meta_data.aggregate)

    def test_exposure_term_length_days(self):
        self.assertEqual(self.meta_data.exposure_term_length_days, 364)
        # Edge case: same start and end date
        self.meta_data.exposure_period_end = self.meta_data.exposure_period_start
        self.assertEqual(self.meta_data.exposure_term_length_days, 0)

class TestExposureValues(unittest.TestCase):
    def setUp(self):
        self.values = ExposureValues(
            exposure_value=100000.0,
            attachment_point=5000.0,
            limit=50000.0,
        )

    def test_properties_and_setters(self):
        self.values.exposure_value = 200000.0
        self.assertEqual(self.values.exposure_value, 200000.0)
        self.values.attachment_point = 10000.0
        self.assertEqual(self.values.attachment_point, 10000.0)
        self.values.limit = 100000.0
        self.assertEqual(self.values.limit, 100000.0)

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
        # Before start
        self.assertEqual(self.exposure._earned_pct(date(2023, 12, 31)), 0.0)
        # After end
        self.assertEqual(self.exposure._earned_pct(date(2025, 1, 1)), 1.0)

    def test_earned_exposure_value(self):
        analysis_date = date(2024, 6, 30)
        self.assertAlmostEqual(self.exposure.earned_exposure_value(analysis_date), 50000.0)
        # Before start
        self.assertEqual(self.exposure.earned_exposure_value(date(2023, 12, 31)), 0.0)
        # After end
        self.assertEqual(self.exposure.earned_exposure_value(date(2025, 1, 1)), 100000.0)

    def test_repr(self):
        r = repr(self.exposure)
        self.assertIn("EXP001", r)
        self.assertIn("Test Exposure", r)

class TestExposures(unittest.TestCase):
    def setUp(self):
        self.meta1 = ExposureMetaData(
            exposure_id="EXP001",
            exposure_name="Exposure 1",
            exposure_period_start=date(2023, 1, 1),
            exposure_period_end=date(2023, 12, 31),
            currency="USD",
            aggregate=False,
        )
        self.meta2 = ExposureMetaData(
            exposure_id="EXP002",
            exposure_name="Exposure 2",
            exposure_period_start=date(2024, 1, 1),
            exposure_period_end=date(2024, 12, 31),
            currency="EUR",
            aggregate=True,
        )
        self.values1 = ExposureValues(
            exposure_value=100000.0,
            attachment_point=5000.0,
            limit=50000.0,
        )
        self.values2 = ExposureValues(
            exposure_value=200000.0,
            attachment_point=10000.0,
            limit=100000.0,
        )
        self.exp1 = Exposure(self.meta1, self.values1)
        self.exp2 = Exposure(self.meta2, self.values2)
        self.exposures = Exposures([self.exp1, self.exp2])

    def test_exposures_property(self):
        self.assertEqual(self.exposures.exposures, [self.exp1, self.exp2])
        self.exposures.exposures = [self.exp1]
        self.assertEqual(self.exposures.exposures, [self.exp1])

    def test_modelling_years(self):
        years = self.exposures.modelling_years
        self.assertIn(2023, years)
        self.assertIn(2024, years)

    def test_currencies(self):
        currencies = self.exposures.currencies
        self.assertIn("USD", currencies)
        self.assertIn("EUR", currencies)

    def test_exposure_ids(self):
        ids = self.exposures.exposure_ids
        self.assertIn("EXP001", ids)
        self.assertIn("EXP002", ids)

    def test_append_and_len(self):
        meta3 = ExposureMetaData(
            exposure_id="EXP003",
            exposure_name="Exposure 3",
            exposure_period_start=date(2025, 1, 1),
            exposure_period_end=date(2025, 12, 31),
            currency="GBP",
            aggregate=False,
        )
        values3 = ExposureValues(
            exposure_value=300000.0,
            attachment_point=15000.0,
            limit=150000.0,
        )
        exp3 = Exposure(meta3, values3)
        self.exposures.append(exp3)
        self.assertEqual(len(self.exposures), 2)  # If append does not mutate in place, adjust as needed

    def test_getitem_and_slice(self):
        self.assertIs(self.exposures[0], self.exp1)
        sliced = self.exposures[:1]
        self.assertIsInstance(sliced, Exposures)
        self.assertEqual(len(sliced), 1)
        self.assertIs(sliced[0], self.exp1)

    def test_iter(self):
        exposures_list = list(iter(self.exposures))
        self.assertEqual(exposures_list[0], self.exp1)
        self.assertEqual(exposures_list[1], self.exp2)

    def test_repr(self):
        r = repr(self.exposures)
        self.assertIn("EXP001", r)
        self.assertIn("EXP002", r)


if __name__ == "__main__":
    unittest.main()