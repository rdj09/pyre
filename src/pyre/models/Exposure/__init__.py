from .exposure_curve_functions import (
    ExposureCurveType,
    mbbefd_curve,
    mixed_exponential_curve,
    riebesell_curve,
    swissRe_c_values,
)
from .exposure_ILF_functions import pareto_ilf, power_ilf
from .exposure_rating_cost import ExposureModel

__all__ = [
    "ExposureModel",
    "ExposureCurveType",
    "mbbefd_curve",
    "mixed_exponential_curve",
    "riebesell_curve",
    "swissRe_c_values",
    "pareto_ilf",
    "power_ilf",
    "ExposureCurveFitter",
    "ILFFitter",
]


def __getattr__(name):
    if name == "ExposureCurveFitter":
        try:
            from .exposure_curve_fitting import ExposureCurveFitter

            return ExposureCurveFitter
        except ImportError as e:
            raise ImportError(
                f'{name} requires the "curve-fitting" optional extra: '
                f'pip install -e ".[curve-fitting]"'
            ) from e
    if name == "ILFFitter":
        try:
            from .exposure_ILF_fitting import ILFFitter

            return ILFFitter
        except ImportError as e:
            raise ImportError(
                f'{name} requires the "curve-fitting" optional extra: '
                f'pip install -e ".[curve-fitting]"'
            ) from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
