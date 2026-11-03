"""Tests for `pyre.models.Exposure`'s public API (task 18).

`Exposure/__init__.py` must eagerly export the scipy-free names
(`ExposureModel`, `ExposureCurveType`, the curve/ILF functions) so importing
`pyre.models.Exposure` never requires scipy/matplotlib, while lazily
exposing `ExposureCurveFitter`/`ILFFitter` (which hard-import scipy) via
`__getattr__`, raising an `ImportError` naming the `curve-fitting` extra when
scipy is not installed.
"""

import unittest


def _scipy_available() -> bool:
    try:
        import scipy  # noqa: F401
    except ImportError:
        return False
    return True


class TestExposureModuleInit(unittest.TestCase):
    def test_exposure_module_imports_without_scipy_installed(self):
        # import pyre.models.Exposure must succeed and expose ExposureModel
        # regardless of scipy's presence
        from pyre.models.Exposure import ExposureModel

        self.assertTrue(callable(ExposureModel))

    def test_exposure_module_exports_curve_and_ilf_functions(self):
        from pyre.models.Exposure import (
            ExposureCurveType,
            mbbefd_curve,
            mixed_exponential_curve,
            pareto_ilf,
            power_ilf,
            riebesell_curve,
            swissRe_c_values,
        )

        self.assertTrue(callable(mbbefd_curve))
        self.assertTrue(callable(mixed_exponential_curve))
        self.assertTrue(callable(riebesell_curve))
        self.assertTrue(callable(pareto_ilf))
        self.assertTrue(callable(power_ilf))
        self.assertIsNotNone(ExposureCurveType)
        self.assertIsNotNone(swissRe_c_values)

    def test_exposure_curve_fitter_lazy_import_error_names_the_extra(self):
        # only meaningful when scipy is NOT installed -- skip if it is
        if _scipy_available():
            self.skipTest("scipy is installed; lazy-import error path not exercised")
        import pyre.models.Exposure as exposure_pkg

        with self.assertRaises(ImportError) as ctx:
            exposure_pkg.ExposureCurveFitter
        self.assertIn("curve-fitting", str(ctx.exception))

    def test_ilf_fitter_lazy_import_error_names_the_extra(self):
        # only meaningful when scipy is NOT installed -- skip if it is
        if _scipy_available():
            self.skipTest("scipy is installed; lazy-import error path not exercised")
        import pyre.models.Exposure as exposure_pkg

        with self.assertRaises(ImportError) as ctx:
            exposure_pkg.ILFFitter
        self.assertIn("curve-fitting", str(ctx.exception))

    def test_unknown_attribute_raises_attribute_error(self):
        import pyre.models.Exposure as exposure_pkg

        with self.assertRaises(AttributeError):
            exposure_pkg.NotARealName

    def test_models_init_exports_exposure_model(self):
        from pyre.models import ExposureModel

        self.assertTrue(callable(ExposureModel))


if __name__ == "__main__":
    unittest.main()
