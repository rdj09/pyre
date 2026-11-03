import unittest
from datetime import date, timedelta
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
        # Actual/actual day count: 2024 is a leap year, so Jan1-Jun30 is 181 of
        # the period's 365 exposure_term_length_days (confirmed by the
        # already-passing test_term_length_days), not an exact calendar-half.
        analysis_date = date(2024, 6, 30)
        self.assertAlmostEqual(self.exposure._earned_pct(analysis_date), 181 / 365)
        # Before start
        self.assertEqual(self.exposure._earned_pct(date(2023, 12, 31)), 0.0)
        # After end
        self.assertEqual(self.exposure._earned_pct(date(2025, 1, 1)), 1.0)

    def test_earned_exposure_value(self):
        analysis_date = date(2024, 6, 30)
        self.assertAlmostEqual(
            self.exposure.earned_exposure_value(analysis_date), 100000.0 * 181 / 365
        )
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
        self.assertEqual(len(self.exposures), 3)

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


class TestExposureAggregateParallelogram(unittest.TestCase):
    """Golden-value and boundary tests for the parallelogram method used by
    ``Exposure._earned_pct`` when ``aggregate=True``.

    Model (Werner & Modlin, *Basic Ratemaking*, 5th ed., CAS 2016, Chapter 5
    "Premium" -- the Parallelogram ("geometric") Method section): policies
    are assumed written uniformly over
    [exposure_period_start, exposure_period_end] (width T days), each with
    its own term of T days (= exposure_term_length_days). The earned
    fraction as of analysis_date is the average, over all uniformly-written
    policies, of each policy's own linear pro-rata earned fraction.

    NOTE ON THE BRIEF'S WORKED EXAMPLE: the task brief that commissioned this
    test described the golden value as occurring at the *calendar mid-year*
    analysis date (7/1 for a 1/1-12/31 period). The geometric derivation
    below (see task-17-report.md for the full by-hand derivation) shows this
    is not where the curve actually equals 0.5 -- by hand, the earned
    fraction turns out to be the CDF, at t = (analysis_date - start).days,
    of the sum of two independent Uniform(0, T) variables (the writing-date
    offset and the elapsed-term offset), whose distribution is symmetric
    about its mean t = T, i.e. about analysis_date == exposure_period_end,
    not about the calendar midpoint of the period. At 1/1-12/31 mid-year
    (t = T/2) this model gives ~0.125, not 0.5. The true "exactly 0.5 by
    symmetry" point -- and the one actually implied by the stated boundary
    condition "analysis_date >= exposure_period_end + term_length -> 1.0"
    together with "written uniformly over [start, end], each with term T"
    -- is exposure_period_end itself. That is also the well-known CAS result
    that exactly half of a uniformly-written annual cohort's exposure has
    earned by the end of its underwriting period. The golden-value test
    below uses that date instead of the brief's literal mid-year date.
    """

    def setUp(self):
        self.meta = ExposureMetaData(
            exposure_id="AGG001",
            exposure_name="Aggregate 2023",
            exposure_period_start=date(2023, 1, 1),
            exposure_period_end=date(2023, 12, 31),
            currency="USD",
            aggregate=True,
        )
        self.values = ExposureValues(
            exposure_value=1_000_000.0, attachment_point=0.0, limit=1_000_000.0
        )
        self.exposure = Exposure(self.meta, self.values)

    def test_earned_pct_aggregate_symmetric_case_matches_geometric_derivation(self):
        """Golden value: by the geometric derivation (see docstring above and
        task-17-report.md), the earned fraction is exactly 0.5 at
        analysis_date == exposure_period_end, by symmetry of the
        triangle/trapezoid-overlap under the uniform-writing assumption."""
        pct = self.exposure._earned_pct(self.meta.exposure_period_end)
        self.assertAlmostEqual(pct, 0.5, places=2)

    def test_earned_pct_aggregate_symmetric_about_period_end(self):
        """General (off-center) check that the curve is a genuine
        two-dimensional triangle/trapezoid-overlap calculation, not a linear
        ramp pinned to a single golden value: earned_pct(end - k) and
        earned_pct(end + k) are complementary for any k, and the curve is
        strictly quadratic (not linear) either side of the period."""
        end = self.meta.exposure_period_end
        for k in (10, 50, 120, 200, 360):
            before = self.exposure._earned_pct(end - timedelta(days=k))
            after = self.exposure._earned_pct(end + timedelta(days=k))
            self.assertAlmostEqual(before + after, 1.0, places=9)

        term = self.meta.exposure_term_length_days
        quarter_term_pct = self.exposure._earned_pct(
            self.meta.exposure_period_start + timedelta(days=term // 4)
        )
        half_term_pct = self.exposure._earned_pct(
            self.meta.exposure_period_start + timedelta(days=term // 2)
        )
        # Quadratic, not linear: doubling t from T/4 to T/2 roughly
        # quadruples the earned fraction (t^2 scaling), it does not merely
        # double it as a straight-line chord would.
        self.assertLess(quarter_term_pct, 0.5 * half_term_pct)

    def test_earned_pct_aggregate_before_period_start_is_zero(self):
        pct = self.exposure._earned_pct(
            self.meta.exposure_period_start - timedelta(days=1)
        )
        self.assertEqual(pct, 0.0)
        # Exactly at the start is also zero (nothing has had time to earn).
        self.assertEqual(self.exposure._earned_pct(self.meta.exposure_period_start), 0.0)

    def test_earned_pct_aggregate_after_period_end_plus_term_is_one(self):
        term = self.meta.exposure_term_length_days
        fully_earned_date = self.meta.exposure_period_end + timedelta(days=term)
        self.assertEqual(self.exposure._earned_pct(fully_earned_date), 1.0)
        # Comfortably past that date is also fully earned.
        self.assertEqual(
            self.exposure._earned_pct(fully_earned_date + timedelta(days=5)), 1.0
        )


if __name__ == "__main__":
    unittest.main()