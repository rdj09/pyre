from typing import Dict, List, Optional, Tuple
from enum import Enum, auto
from math import exp
from ..claims.claims import Claims
from ..models.Experience.curve_fitting import (
    exponential_fit,
    power_fit,
    weibull_fit,
    inverse_power_fit,
    r_squared,
    assess_error_assumptions,
)


class CurveType(Enum):
    """
    Enum representing different types of curves that can be fitted to triangle data.
    """

    EXPONENTIAL = auto()
    POWER = auto()
    WEIBULL = auto()
    INVERSE_POWER = auto()
    OTHER = auto()


class Triangle:
    """
    Represents a triangle of claim values (e.g., paid or incurred) by origin (modelling) year and development period.

    The triangle is stored as a nested dictionary where:
    - The outer key is the origin year (int)
    - The inner key is the development period (int)
    - The value is the claim amount (float)

    Example structure:
    {
        2020: {1: 100.0, 2: 150.0, 3: 175.0},
        2021: {1: 110.0, 2: 165.0},
        2022: {1: 120.0}
    }
    """

    def __init__(
        self,
        triangle: Optional[Dict[int, Dict[int, float]]] = None,
        origin_years: Optional[List[int]] = None,
        dev_periods: Optional[List[int]] = None,
    ):
        """
        Initialize a Triangle directly or as an empty structure.

        Args:
            triangle: Dictionary mapping origin years to dictionaries mapping development periods to values
            origin_years: List of origin years in the triangle
            dev_periods: List of development periods in the triangle
        """
        self.triangle = triangle if triangle is not None else {}

        # If origin_years not provided, extract from triangle keys
        if origin_years is None:
            self.origin_years = sorted(self.triangle.keys()) if self.triangle else []
        else:
            self.origin_years = sorted(origin_years)

        # If dev_periods not provided, extract from all inner dictionaries
        if dev_periods is None:
            all_dev_periods = set()
            for year_data in self.triangle.values():
                all_dev_periods.update(year_data.keys())
            self.dev_periods = sorted(all_dev_periods) if all_dev_periods else []
        else:
            self.dev_periods = sorted(dev_periods)

        # Validate the triangle structure
        self._validate_triangle()

    def _validate_triangle(self) -> None:
        """
        Validate the triangle structure to ensure all keys are integers
        and all values are numeric.

        Raises:
            ValueError: If the triangle structure is invalid
        """
        for origin_year, dev_data in self.triangle.items():
            if not isinstance(origin_year, int):
                raise ValueError(f"Origin year must be an integer, got {type(origin_year)}")

            for dev_period, value in dev_data.items():
                if not isinstance(dev_period, int):
                    raise ValueError(
                        f"Development period must be an integer, got {type(dev_period)}"
                    )

                if value is not None and not isinstance(value, (int, float)):
                    raise ValueError(f"Triangle values must be numeric or None, got {type(value)}")

    def __repr__(self) -> str:
        """Return a string representation of the Triangle object."""
        return f"Triangle(origin_years={self.origin_years}, dev_periods={self.dev_periods})"

    def __str__(self) -> str:
        """Return a formatted string representation of the triangle."""
        if not self.triangle:
            return "Empty Triangle"

        # Create header row
        header = "Origin Year | " + " | ".join(f"Dev {d}" for d in self.dev_periods)

        # Create rows for each origin year
        rows = []
        for oy in self.origin_years:
            row_values = []
            for dp in self.dev_periods:
                value = self.triangle.get(oy, {}).get(dp)
                row_values.append(f"{value:.2f}" if value is not None else "N/A")
            rows.append(f"{oy} | " + " | ".join(row_values))

        return header + "\n" + "\n".join(rows)

    def __getitem__(self, key: Tuple[int, int]) -> Optional[float]:
        """
        Get a value from the triangle using tuple indexing.

        Args:
            key: Tuple of (origin_year, development_period)

        Returns:
            The value at the specified position or None if not found

        Example:
            value = triangle[2020, 2]  # Gets the value for origin year 2020, development period 2
        """
        origin_year, dev_period = key
        return self.triangle.get(origin_year, {}).get(dev_period)

    def __setitem__(self, key: Tuple[int, int], value: Optional[float]) -> None:
        """
        Set a value in the triangle using tuple indexing.

        Args:
            key: Tuple of (origin_year, development_period)
            value: The value to set

        Example:
            triangle[2020, 2] = 150.0  # Sets the value for origin year 2020, development period 2
        """
        origin_year, dev_period = key

        # Ensure the origin year exists in the triangle
        if origin_year not in self.triangle:
            self.triangle[origin_year] = {}
            if origin_year not in self.origin_years:
                self.origin_years.append(origin_year)
                self.origin_years.sort()

        # Set the value
        self.triangle[origin_year][dev_period] = value

        # Update dev_periods if needed
        if dev_period not in self.dev_periods:
            self.dev_periods.append(dev_period)
            self.dev_periods.sort()

    def get_value(self, origin_year: int, dev_period: int) -> Optional[float]:
        """
        Get a value from the triangle.

        Args:
            origin_year: The origin year
            dev_period: The development period

        Returns:
            The value at the specified position or None if not found
        """
        return self.triangle.get(origin_year, {}).get(dev_period)

    def set_value(self, origin_year: int, dev_period: int, value: Optional[float]) -> None:
        """
        Set a value in the triangle.

        Args:
            origin_year: The origin year
            dev_period: The development period
            value: The value to set
        """
        self[origin_year, dev_period] = value

    def get_latest_diagonal(self) -> Dict[int, float]:
        """
        Get the latest diagonal of the triangle.

        Returns:
            Dictionary mapping origin years to their latest available values
        """
        result = {}
        for oy in self.origin_years:
            # Find the maximum development period with a value for this origin year
            available_devs = [dp for dp in self.dev_periods if self.get_value(oy, dp) is not None]
            if available_devs:
                max_dev = max(available_devs)
                result[oy] = self.get_value(oy, max_dev)
        return result

    def to_incremental(self) -> "Triangle":
        """
        Convert a cumulative triangle to an incremental triangle.

        Returns:
            A new Triangle with incremental values
        """
        incremental_triangle = {}

        for oy in self.origin_years:
            incremental_triangle[oy] = {}
            prev_value = None

            for dp in self.dev_periods:
                current_value = self.get_value(oy, dp)

                if current_value is None:
                    incremental_triangle[oy][dp] = None
                elif prev_value is None:
                    incremental_triangle[oy][dp] = current_value
                else:
                    incremental_triangle[oy][dp] = current_value - prev_value

                if current_value is not None:
                    prev_value = current_value

        return Triangle(
            triangle=incremental_triangle,
            origin_years=self.origin_years.copy(),
            dev_periods=self.dev_periods.copy(),
        )

    def to_cumulative(self) -> "Triangle":
        """
        Convert an incremental triangle to a cumulative triangle.

        Returns:
            A new Triangle with cumulative values
        """
        cumulative_triangle = {}

        for oy in self.origin_years:
            cumulative_triangle[oy] = {}
            cumulative_value = 0.0

            for dp in self.dev_periods:
                incremental_value = self.get_value(oy, dp)

                if incremental_value is None:
                    cumulative_triangle[oy][dp] = None
                else:
                    cumulative_value += incremental_value
                    cumulative_triangle[oy][dp] = cumulative_value

        return Triangle(
            triangle=cumulative_triangle,
            origin_years=self.origin_years.copy(),
            dev_periods=self.dev_periods.copy(),
        )

    @classmethod
    def from_claims(cls, claims: Claims, value_type: str = "incurred") -> "Triangle":
        """
        Construct a Triangle from a Claims object.

        Args:
            claims: Claims object containing claim data
            value_type: Type of values to extract, either "incurred" or "paid"

        Returns:
            A new Triangle object with aggregated claim values

        Raises:
            ValueError: If value_type is not "incurred" or "paid"
        """
        if value_type not in ["incurred", "paid"]:
            raise ValueError(f"value_type must be 'incurred' or 'paid', got '{value_type}'")

        # Collect all unique modelling years
        origin_years = claims.modelling_years

        # Build the triangle, tracking development periods actually seen.
        # Note: Claims.development_periods returns per-claim month *sequences*
        # (its own pre-existing, separately-tracked quirk), not the flat set
        # of period values this method needs -- so build that set here.
        triangle: Dict[int, Dict[int, float]] = {year: {} for year in origin_years}
        dev_periods_seen: set = set()

        # Aggregate claims by origin year and development period
        for claim in claims:
            origin_year = claim.claims_meta_data.modelling_year

            # Get the appropriate development history based on value_type
            if value_type == "incurred":
                dev_history = claim.capped_claim_development_history.cumulative_dev_incurred
            else:  # value_type == "paid"
                dev_history = claim.capped_claim_development_history.cumulative_dev_paid
            dev_months = claim.capped_claim_development_history.development_months

            # Add values to the triangle
            for dev_period, value in zip(dev_months, dev_history):
                dev_periods_seen.add(dev_period)
                if dev_period not in triangle[origin_year]:
                    triangle[origin_year][dev_period] = 0.0
                triangle[origin_year][dev_period] += value

        dev_periods = sorted(dev_periods_seen)

        return cls(triangle=triangle, origin_years=origin_years, dev_periods=dev_periods)

    def calculate_age_to_age_factors(self) -> Dict[int, Dict[int, float]]:
        """
        Calculate age-to-age factors for the triangle.

        Age-to-age factors are calculated as the ratio of the value at development period j+1
        to the value at development period j for each origin year.

        Returns:
            Dict[int, Dict[int, float]]: A dictionary mapping origin years to dictionaries
                mapping development periods to age-to-age factors.
        """
        factors = {}

        for oy in self.origin_years:
            factors[oy] = {}
            for i in range(len(self.dev_periods) - 1):
                current_dev = self.dev_periods[i]
                next_dev = self.dev_periods[i + 1]

                current_value = self.get_value(oy, current_dev)
                next_value = self.get_value(oy, next_dev)

                if current_value is not None and next_value is not None and current_value != 0:
                    factors[oy][current_dev] = next_value / current_value

        return factors

    def get_average_age_to_age_factors(self, method: str = "simple") -> Dict[int, float]:
        """
        Calculate average age-to-age factors across all origin years.

        Args:
            method (str): Method to use for averaging. Options are:
                - "simple": Simple arithmetic mean
                - "volume": Volume-weighted average

        Returns:
            Dict[int, float]: A dictionary mapping development periods to average age-to-age factors.
        """
        factors = self.calculate_age_to_age_factors()
        avg_factors = {}

        for dev_idx in range(len(self.dev_periods) - 1):
            dev = self.dev_periods[dev_idx]

            if method == "simple":
                # Simple average
                dev_factors = [
                    factors[oy].get(dev) for oy in self.origin_years if dev in factors.get(oy, {})
                ]
                dev_factors = [f for f in dev_factors if f is not None]

                if dev_factors:
                    avg_factors[dev] = sum(dev_factors) / len(dev_factors)

            elif method == "volume":
                # Volume-weighted average
                numerator_sum = 0.0
                denominator_sum = 0.0

                for oy in self.origin_years:
                    current_value = self.get_value(oy, dev)
                    next_value = self.get_value(oy, self.dev_periods[dev_idx + 1])

                    if current_value is not None and next_value is not None and current_value != 0:
                        numerator_sum += next_value
                        denominator_sum += current_value

                if denominator_sum != 0:
                    avg_factors[dev] = numerator_sum / denominator_sum

        return avg_factors

    def fit_curve(
        self, curve_type: CurveType, c_values: List[float] = None
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Fit a curve to the average age-to-age factors.

        Args:
            curve_type (CurveType): Type of curve to fit. Options are:
                - CurveType.EXPONENTIAL: Exponential curve
                - CurveType.POWER: Power curve
                - CurveType.WEIBULL: Weibull curve
                - CurveType.INVERSE_POWER: Inverse power curve (Sherman)
            c_values (List[float], optional): List of candidate c values for inverse power fit.
                Defaults to [0.5, 1.0, 1.5, 2.0, 2.5, 3.0].

        Returns:
            Tuple[Dict[str, float], Dict[str, float]]: A tuple containing:
                - Parameters of the fitted curve
                - Metrics assessing the quality of the fit
        """
        if c_values is None:
            c_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

        # Get average age-to-age factors
        avg_factors = self.get_average_age_to_age_factors()

        # Prepare data for curve fitting
        dev_periods = sorted(avg_factors.keys())
        factors = [avg_factors[dp] for dp in dev_periods]

        # Fit the appropriate curve
        if curve_type == CurveType.EXPONENTIAL:
            a, b = exponential_fit(factors, dev_periods)
            params = {"a": a, "b": b}
            expected = [1 + exp(a + b * dp) for dp in dev_periods]
            num_params = 2

        elif curve_type == CurveType.POWER:
            a, b = power_fit(factors, dev_periods)
            params = {"a": a, "b": b}
            expected = [a * (b**dp) for dp in dev_periods]
            num_params = 2

        elif curve_type == CurveType.WEIBULL:
            a, b = weibull_fit(factors, dev_periods)
            params = {"a": a, "b": b}
            expected = [1 / (1 - exp(-a * (dp**b))) for dp in dev_periods]
            num_params = 2

        elif curve_type == CurveType.INVERSE_POWER:
            a, b, c = inverse_power_fit(factors, dev_periods, c_values)
            params = {"a": a, "b": b, "c": c}
            expected = [1 + a * ((dp + c) ** b) for dp in dev_periods]
            num_params = 3

        else:
            raise ValueError(f"Unknown curve type: {curve_type}")

        # Calculate fit metrics
        r_squared_value = r_squared(factors, expected)
        error_metrics = assess_error_assumptions(factors, expected, num_params)

        metrics = {"r_squared": r_squared_value, **error_metrics}

        return params, metrics

    def get_selected_development_pattern(
        self,
        curve_type: CurveType,
        tail_factor: float = 1.0,
        c_values: List[float] = None,
    ) -> Dict[int, float]:
        """
        Fit the selected curve type to this triangle's average age-to-age
        factors and derive the resulting *cumulative-to-ultimate* development
        pattern -- consumable by `BurnCostModel(..., development_pattern=...)`.

        For each development period, the cumulative-to-ultimate factor is the
        product of the fitted incremental age-to-age factors for every later
        development period, multiplied by `tail_factor` to project the final
        observed period to ultimate. The factors decrease monotonically as
        development period increases, reaching `tail_factor` at the final
        (latest) development period.

        Args:
            curve_type (CurveType): Type of curve to fit (see `fit_curve`).
            tail_factor (float, optional): Factor applied beyond the final
                observed development period to project to ultimate. Defaults
                to 1.0 (no development tail beyond the data).
            c_values (List[float], optional): Candidate c values for the
                inverse power fit. Defaults to `fit_curve`'s default.

        Returns:
            Dict[int, float]: Mapping of development period to
                cumulative-to-ultimate development factor.
        """
        params, _ = self.fit_curve(curve_type, c_values)

        # Reconstruct the fitted *incremental* age-to-age factor for each
        # "from" development period, reusing fit_curve's own `expected`
        # formulas (not re-derived) -- one entry per period that has a
        # transition to a later period, i.e. all but the last dev period.
        fitted_ata: Dict[int, float] = {}
        for dp in self.dev_periods[:-1]:
            if curve_type == CurveType.EXPONENTIAL:
                fitted_ata[dp] = 1 + exp(params["a"] + params["b"] * dp)
            elif curve_type == CurveType.POWER:
                fitted_ata[dp] = params["a"] * (params["b"] ** dp)
            elif curve_type == CurveType.WEIBULL:
                fitted_ata[dp] = 1 / (1 - exp(-params["a"] * (dp ** params["b"])))
            elif curve_type == CurveType.INVERSE_POWER:
                fitted_ata[dp] = 1 + params["a"] * ((dp + params["c"]) ** params["b"])
            else:
                raise ValueError(f"Unknown curve type: {curve_type}")

        # Cumulative-to-ultimate factor at each dev period is the product of
        # every later incremental factor, times the tail factor -- so walk
        # the dev periods from latest to earliest, accumulating as we go.
        pattern: Dict[int, float] = {}
        if not self.dev_periods:
            return pattern

        reversed_periods = list(reversed(self.dev_periods))
        cumulative = tail_factor
        pattern[reversed_periods[0]] = cumulative
        for dp in reversed_periods[1:]:
            cumulative *= fitted_ata[dp]
            pattern[dp] = cumulative

        return pattern


# TODO IBNER methodology citation of source SCHNIEPER https://www.casact.org/sites/default/files/database/astin_vol21no1_111.pdf
class IBNERPatternExtractor:
    """
    Extracts IBNER patterns from either a Claims object or a Triangle object.
    """

    def __init__(self, triangle: Triangle):
        self.triangle = triangle.triangle
        self.origin_years = triangle.origin_years
        self.dev_periods = triangle.dev_periods

        self._N_triangle: Dict[int, Dict[int, float]] = {oy: {} for oy in self.origin_years}
        self._D_triangle: Dict[int, Dict[int, float]] = {oy: {} for oy in self.origin_years}
        self._compute_N_and_D()

    def _compute_N_and_D(self):
        """
        Compute the N (cumulative) and D (age-to-age development factor) triangles.
        """
        for oy in self.origin_years:
            cumulative = [self.triangle.get(oy, {}).get(d) for d in self.dev_periods]
            for idx, d in enumerate(self.dev_periods):
                current = cumulative[idx]
                if current is None:
                    self._N_triangle[oy][d] = None
                    self._D_triangle[oy][d] = None
                    continue

                self._N_triangle[oy][d] = current
                if idx == 0:
                    # Raw value here; get_D_triangle() normalizes the first period to 1.0.
                    self._D_triangle[oy][d] = current
                else:
                    prev = cumulative[idx - 1]
                    self._D_triangle[oy][d] = (current / prev) if prev is not None else None

    def get_N_triangle(self) -> Triangle:
        """
        Returns the N triangle (cumulative values) as a Triangle instance.
        """
        return Triangle(triangle=self._N_triangle)

    def get_D_triangle(self) -> Triangle:
        """
        Returns the D triangle (age-to-age development factors, first period normalized to 1.0).
        """
        normalized: Dict[int, Dict[int, float]] = {}
        for oy in self.origin_years:
            normalized[oy] = {}
            for idx, d in enumerate(self.dev_periods):
                value = self._D_triangle[oy].get(d)
                if value is None:
                    continue
                normalized[oy][d] = 1.0 if idx == 0 else value
        return Triangle(triangle=normalized)

    def get_IBNER_pattern(self) -> Dict[int, float]:
        """
        Returns, per origin year, the product of the average age-to-age development
        factors for every development period after that year's latest available data.
        """
        d_triangle = self.get_D_triangle().triangle
        avg_ratio: Dict[int, float] = {}
        for d in self.dev_periods:
            vals = [d_triangle[oy][d] for oy in self.origin_years if d in d_triangle.get(oy, {})]
            if vals:
                avg_ratio[d] = sum(vals) / len(vals)

        pattern: Dict[int, float] = {}
        for oy in self.origin_years:
            available = [d for d in self.dev_periods if d in self.triangle.get(oy, {})]
            latest = max(available) if available else None
            factor = 1.0
            if latest is not None:
                for d in self.dev_periods:
                    if d > latest:
                        factor *= avg_ratio.get(d, 1.0)
            pattern[oy] = factor
        return pattern
