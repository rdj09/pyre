"""Tests for ExposureCurveFitter / select_best_curve and their integration into
ExposureModel.from_fitted_curve (task 16).

These all depend on the `curve-fitting` extra (numpy, scipy, matplotlib) --
`exposure_curve_fitting.py` hard-imports `scipy.optimize`, `numpy`, and
`matplotlib.pyplot` at module level. Per CLAUDE.md, without that extra
installed this file must SKIP at collection, not error -- hence the
`pytest.importorskip` guards below, mirroring `tests/test_io_excel.py`'s
`HAS_OPENPYXL` skip-without-extra pattern (there via try/except ImportError +
`unittest.skipUnless`; here via `importorskip`, since this file is not
unittest.TestCase-based).
"""

from datetime import date

import pytest

numpy = pytest.importorskip(
    "numpy", reason="requires the curve-fitting extra: pip install -e '.[curve-fitting]'"
)
pytest.importorskip(
    "scipy", reason="requires the curve-fitting extra: pip install -e '.[curve-fitting]'"
)
pytest.importorskip(
    "matplotlib", reason="requires the curve-fitting extra: pip install -e '.[curve-fitting]'"
)

from pyre import (  # noqa: E402
    Exposure,
    ExposureMetaData,
    Exposures,
    ExposureValues,
    RIContract,
    RIContractMetadata,
    RILayer,
)
from pyre.models.Exposure.exposure_curve_fitting import (  # noqa: E402
    ExposureCurveFitter,
    select_best_curve,
)
from pyre.models.Exposure.exposure_curve_functions import (  # noqa: E402
    ExposureCurveType,
    mbbefd_curve,
    mixed_exponential_curve,
    riebesell_curve,
)
from pyre.models.Exposure.exposure_rating_cost import ExposureModel  # noqa: E402
from pyre.treaty import ClaimTriggerBasis, ContractType, IndexationClauseType  # noqa: E402


def _build_contract(layers):
    metadata = RIContractMetadata(
        contract_id="C-0001",
        contract_description="Test",
        cedent_name="Acme Re",
        trigger_basis=ClaimTriggerBasis.LOD,
        indexation_clause=IndexationClauseType.FULL_INDEXATION,
        indexation_margin=0.0,
        inception_date=date(2023, 1, 1),
        expiration_date=date(2023, 12, 31),
        fx_rates={"USD": 1.0},
    )
    return RIContract(contract_meta_data=metadata, layers=layers)


def _build_layer(layer_id, occurrence_attachment, occurrence_limit):
    return RILayer(
        layer_id=layer_id,
        layer_name=f"Layer {layer_id}",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=occurrence_attachment,
        occurrence_limit=occurrence_limit,
        aggregate_attachment=0.0,
        aggregate_limit=0.0,
        subject_lines_of_business=[],
        subject_lob_exposure_amounts=[],
        full_subject_premium=0.0,
        written_line=1.0,
        signed_line=1.0,
        number_of_reinstatements=0,
        reinstatement_cost={},
    )


def _build_exposure(exposure_id, attachment_point, limit):
    meta = ExposureMetaData(
        exposure_id=exposure_id,
        exposure_name=exposure_id,
        exposure_period_start=date(2023, 1, 1),
        exposure_period_end=date(2023, 12, 31),
        currency="USD",
    )
    values = ExposureValues(
        exposure_value=attachment_point + limit,
        attachment_point=attachment_point,
        limit=limit,
    )
    return Exposure(exposure_meta=meta, exposure_values=values)


def test_riebesell_fitting_recovers_true_parameter():
    """Fitting noiseless data generated from a known Riebesell curve should
    recover the true z parameter and give a near-perfect R-squared."""
    positions = numpy.linspace(0.1, 1.0, 20)
    true_z = 2.0
    values = [riebesell_curve(0, pos, true_z, 1.0) for pos in positions]

    fitter = ExposureCurveFitter(positions, values)
    z_value, r_squared = fitter.fit_riebesell()

    assert r_squared > 0.999
    assert abs(z_value - true_z) < 0.1


def test_mbbefd_fitting_recovers_true_parameter():
    """Fitting noiseless data generated from a known MBBEFD curve should
    recover the true c parameter and give a near-perfect R-squared."""
    positions = numpy.linspace(0.1, 1.0, 20)
    true_c = 3.0
    values = [mbbefd_curve(true_c, pos) for pos in positions]

    fitter = ExposureCurveFitter(positions, values)
    c_value, r_squared = fitter.fit_mbbefd()

    assert r_squared > 0.999
    assert abs(c_value - true_c) < 0.1


def test_mixed_exponential_fitting_achieves_high_r_squared():
    """Mixed-exponential parameters aren't uniquely identifiable (several
    (mu, weight) combinations can produce the same curve), so only the
    resulting fit quality -- not the recovered parameters themselves -- is
    asserted here."""
    positions = numpy.linspace(0.1, 1.0, 20)
    true_mus = [0.2, 0.5, 0.8]
    true_weights = [0.3, 0.4, 0.3]
    values = [mixed_exponential_curve(true_mus, true_weights, pos) for pos in positions]

    fitter = ExposureCurveFitter(positions, values)
    mus, weights, r_squared = fitter.fit_mixed_exponential(num_components=3)

    assert r_squared > 0.99
    assert len(mus) == 3
    assert len(weights) == 3
    assert abs(sum(weights) - 1.0) < 1e-6


def test_fit_all_curves_returns_r_squared_for_every_successful_fit():
    positions = numpy.linspace(0.1, 1.0, 20)
    true_c = 3.0
    values = [mbbefd_curve(true_c, pos) for pos in positions]

    fitter = ExposureCurveFitter(positions, values)
    results = fitter.fit_all_curves()

    assert "MBBEFD" in results
    # Every successfully-fitted curve's result tuple ends in an R-squared
    # value, and a near-exact MBBEFD fit on MBBEFD-generated data should be
    # very high.
    for params in results.values():
        assert 0.0 <= params[-1] <= 1.0 + 1e-9
    assert results["MBBEFD"][-1] > 0.999


def test_select_best_curve_picks_a_high_quality_fit():
    positions = numpy.linspace(0.1, 1.0, 20)
    true_c = 3.0
    values = [mbbefd_curve(true_c, pos) for pos in positions]

    best_curve, params, r_squared = select_best_curve(positions, values)

    assert isinstance(best_curve, ExposureCurveType)
    assert r_squared > 0.99
    assert isinstance(params, dict)


class TestFromFittedCurve:
    """Covers task 16: ExposureModel.from_fitted_curve(fitter, exposures,
    ri_contract) classmethod, wiring ExposureCurveFitter's best-fit output
    into ExposureModel."""

    def test_from_fitted_curve_builds_usable_exposure_model(self):
        positions = numpy.linspace(0.1, 1.0, 20)
        true_c = 3.0
        values = [mbbefd_curve(true_c, pos) for pos in positions]
        fitter = ExposureCurveFitter(positions, values)

        exposure = _build_exposure("EXP001", attachment_point=0.0, limit=1_000_000.0)
        exposures = Exposures([exposure])
        layer = _build_layer(
            layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0
        )
        contract = _build_contract([layer])

        model = ExposureModel.from_fitted_curve(
            fitter, exposures=exposures, ri_contract=contract
        )
        shares = model.calculate_all_shares()

        assert all(
            0.0 <= v <= 1.0 for layer_shares in shares.values() for v in layer_shares.values()
        )

    def test_from_fitted_curve_selects_curve_with_highest_r_squared(self):
        positions = numpy.linspace(0.1, 1.0, 20)
        true_c = 3.0
        values = [mbbefd_curve(true_c, pos) for pos in positions]
        fitter = ExposureCurveFitter(positions, values)

        expected_curve_type, expected_params, expected_r_squared = select_best_curve(
            positions, values
        )

        exposures = Exposures([_build_exposure("EXP001", 0.0, 1_000_000.0)])
        contract = _build_contract(
            [_build_layer(layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0)]
        )

        model = ExposureModel.from_fitted_curve(
            fitter, exposures=exposures, ri_contract=contract
        )

        assert expected_r_squared > 0.0
        assert model._selected_curve == expected_curve_type
        assert model._curve_parameters.keys() == expected_params.keys()

    def test_from_fitted_curve_passes_through_ilf_function(self):
        from functools import partial

        from pyre.models.Exposure.exposure_ILF_functions import pareto_ilf

        positions = numpy.linspace(0.1, 1.0, 20)
        values = [mbbefd_curve(3.0, pos) for pos in positions]
        fitter = ExposureCurveFitter(positions, values)

        exposures = Exposures([_build_exposure("EXP001", 0.0, 1_000_000.0)])
        contract = _build_contract(
            [_build_layer(layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=400_000.0)]
        )
        ilf_function = partial(pareto_ilf, 100_000.0, alpha=1.5, x_m=100_000.0)

        model = ExposureModel.from_fitted_curve(
            fitter,
            exposures=exposures,
            ri_contract=contract,
            ilf_function=ilf_function,
        )

        rate_at_base = model.calculate_ilf_adjusted_rate(
            base_limit=100_000.0, target_limit=100_000.0
        )
        rate_at_higher = model.calculate_ilf_adjusted_rate(
            base_limit=100_000.0, target_limit=500_000.0
        )
        assert rate_at_higher > rate_at_base

    def test_from_fitted_curve_raises_if_no_curve_fits(self):
        # A fitter with no observations at all produces an R-squared of NaN
        # for every curve type (ss_total is 0/0 over an empty array), and
        # "nan > best_r_squared" is never True -- so from_fitted_curve's
        # best-curve search never selects a winner and must surface that as
        # a ValueError, not a raw KeyError/IndexError from best_curve_name
        # staying None.
        fitter = ExposureCurveFitter([], [])

        exposures = Exposures([_build_exposure("EXP001", 0.0, 1_000_000.0)])
        contract = _build_contract([])

        with pytest.raises(ValueError):
            ExposureModel.from_fitted_curve(fitter, exposures=exposures, ri_contract=contract)


def test_fitted_curve_through_calculate_all_shares_e2e():
    """Task 23: proves the full pipeline wires together end-to-end --
    synthetic (position, value) observations -> ExposureCurveFitter.fit_all_curves
    -> ExposureModel.from_fitted_curve -> calculate_all_shares.

    Every resulting share must lie in [0, 1]. As a second check, two
    same-width layers at different attachment points must price with the
    lower-attaching layer getting the larger share -- the fitted curve is
    concave (MBBEFD-generated data), so marginal exposure share shrinks
    moving up the tower.
    """
    positions = numpy.linspace(0.1, 1.0, 20)
    true_c = 3.0
    values = [mbbefd_curve(true_c, pos) for pos in positions]
    fitter = ExposureCurveFitter(positions, values)

    exposure = _build_exposure("EXP001", attachment_point=0.0, limit=1_000_000.0)
    exposures = Exposures([exposure])
    layer_low = _build_layer(
        layer_id=1, occurrence_attachment=100_000.0, occurrence_limit=200_000.0
    )
    layer_high = _build_layer(
        layer_id=2, occurrence_attachment=500_000.0, occurrence_limit=200_000.0
    )
    contract = _build_contract([layer_low, layer_high])

    model = ExposureModel.from_fitted_curve(fitter, exposures=exposures, ri_contract=contract)
    shares = model.calculate_all_shares()

    for layer_shares in shares.values():
        share_values = list(layer_shares.values())
        assert all(0.0 <= v <= 1.0 for v in share_values)

    assert shares["EXP001"][1] > shares["EXP001"][2]
