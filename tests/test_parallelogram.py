from datetime import date, timedelta

import pytest

from src.pyre.enums import ExposureBasis
from src.pyre.exposures.exposures import Exposure, ExposureMetaData, ExposureValues


def _make_aggregate_exposure(start: date, end: date) -> Exposure:
    meta = ExposureMetaData(
        exposure_id="E1",
        exposure_name="Aggregate 2020",
        exposure_period_start=start,
        exposure_period_end=end,
        currency="GBP",
        aggregate=True,
        exposure_type=ExposureBasis.WRITTEN,
    )
    return Exposure(meta, ExposureValues(1_000_000.0, 0.0, 1_000_000.0))


def test_parallelogram_returns_zero_before_start():
    exp = _make_aggregate_exposure(date(2020, 1, 1), date(2020, 12, 31))
    pct = exp._earned_pct(date(2019, 12, 31))
    assert pct == pytest.approx(0.0)


def test_parallelogram_returns_one_after_all_policies_expire():
    exp = _make_aggregate_exposure(date(2020, 1, 1), date(2020, 12, 31))
    term_days = (date(2020, 12, 31) - date(2020, 1, 1)).days
    fully_earned_date = date(2020, 12, 31) + timedelta(days=term_days + 1)
    pct = exp._earned_pct(fully_earned_date)
    assert pct == pytest.approx(1.0)


def test_parallelogram_midpoint():
    exp = _make_aggregate_exposure(date(2020, 1, 1), date(2020, 12, 31))
    (date(2020, 12, 31) - date(2020, 1, 1)).days
    mid = date(2020, 1, 1) + timedelta(days=364)
    pct = exp._earned_pct(mid)
    assert 0.45 < pct < 0.55


def test_parallelogram_analysis_at_period_end():
    exp = _make_aggregate_exposure(date(2020, 1, 1), date(2020, 12, 31))
    pct = exp._earned_pct(date(2020, 12, 31))
    assert 0.40 < pct < 0.60


def test_non_aggregate_exposure_not_affected():
    meta = ExposureMetaData(
        exposure_id="E2",
        exposure_name="Normal",
        exposure_period_start=date(2020, 1, 1),
        exposure_period_end=date(2020, 12, 31),
        currency="GBP",
        aggregate=False,
        exposure_type=ExposureBasis.WRITTEN,
    )
    exp = Exposure(meta, ExposureValues(1_000_000.0, 0.0, 1_000_000.0))
    pct = exp._earned_pct(date(2020, 7, 2))
    assert 0.45 < pct < 0.55
