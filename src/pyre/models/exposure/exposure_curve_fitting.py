#citation : https://pep.vse.cz/pdfs/pep/2019/02/01.pdf // https://doi.org/10.18267/j.pep.683
# EXPOSURE MODELLING IN PROPERTY REINSURANCE Jan Hrevuš,1Luboš Marek

import numpy as np
from scipy import optimize
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional, Union, Callable
from .exposure_curve_functions import ExposureCurveType, riebesell_curve, mixed_exponential_curve, mbbefd_curve, swissRe_c_values

class ExposureCurveFitter:
    """
    Class for fitting exposure curves using various methods.

    This class implements methods for fitting exposure curves to data,
    including Riebesell, Mixed Exponential, and MBBEFD curves.

    Based on the paper: "EXPOSURE MODELLING IN PROPERTY REINSURANCE" 
    by Jan Hrevuš and Luboš Marek
    """

    def __init__(self, positions: List[float], values: List[float], base_value: float = 1.0):
        """
        Initialize the exposure curve fitter with observed positions and values.

        Args:
            positions: List of relative positions on the curve (typically normalized to [0,1])
            values: List of observed curve values corresponding to the positions
            base_value: The base value used for normalization (default: 1.0)
        """
        self.positions = np.array(positions)
        self.values = np.array(values)
        self.base_value = base_value

        # Validate inputs
        if len(self.positions) != len(self.values):
            raise ValueError("Positions and values must have the same length")
        if not all(0 <= x <= 1 for x in self.positions):
            raise ValueError("All positions must be between 0 and 1")
        if not all(x >= 0 for x in self.values):
            raise ValueError("All values must be non-negative")

    def fit_riebesell(self) -> Tuple[float, float]:
        """
        Fit a Riebesell curve to the observed data.

        The Riebesell curve has the form: value = (position/base_position)^log(1+z, 2)

        Returns:
            Tuple containing:
                - z parameter
                - R-squared value of the fit
        """
        def objective_function(params):
            z_value = params[0]
            predicted_values = [riebesell_curve(0, pos, z_value, self.base_value) for pos in self.positions]
            return np.sum((np.array(predicted_values) - self.values)**2)

        # Initial guess for parameter
        initial_guess = [1.0]

        # Bounds for parameter (z > 0)
        bounds = [(0.001, 10)]

        # Optimize to find the best parameter
        result = optimize.minimize(objective_function, initial_guess, bounds=bounds, method='L-BFGS-B')

        if not result.success:
            raise RuntimeError(f"Optimization failed: {result.message}")

        z_value = result.x[0]

        # Calculate predicted values
        predicted_values = [riebesell_curve(0, pos, z_value, self.base_value) for pos in self.positions]

        # Calculate R-squared
        ss_total = np.sum((self.values - np.mean(self.values))**2)
        ss_residual = np.sum((self.values - np.array(predicted_values))**2)
        r_squared = 1 - (ss_residual / ss_total)

        return z_value, r_squared

    def fit_mixed_exponential(self, num_components: int = 3) -> Tuple[List[float], List[float], float]:
        """
        Fit a mixed exponential curve to the observed data.

        The mixed exponential curve is a weighted sum of exponential components.

        Args:
            num_components: Number of exponential components to use (default: 3)

        Returns:
            Tuple containing:
                - List of mu parameters
                - List of weight parameters
                - R-squared value of the fit
        """
        def objective_function(params):
            # Split params into mus and weights
            mus = params[:num_components]
            weights = params[num_components:]

            # Normalize weights to sum to 1
            weights = weights / np.sum(weights)

            predicted_values = [mixed_exponential_curve(mus, weights, pos) for pos in self.positions]
            return np.sum((np.array(predicted_values) - self.values)**2)

        # Initial guess for parameters
        # Spread mus across a reasonable range
        initial_mus = np.linspace(0.1, 1.0, num_components)
        # Equal weights initially
        initial_weights = np.ones(num_components) / num_components
        initial_guess = np.concatenate([initial_mus, initial_weights])

        # Bounds for parameters (mus > 0, weights > 0)
        bounds = [(0.001, 10)] * num_components + [(0.001, 1)] * num_components

        # Optimize to find the best parameters
        result = optimize.minimize(objective_function, initial_guess, bounds=bounds, method='L-BFGS-B')

        if not result.success:
            raise RuntimeError(f"Optimization failed: {result.message}")

        # Extract and normalize parameters
        mus = result.x[:num_components]
        weights = result.x[num_components:]
        weights = weights / np.sum(weights)

        # Calculate predicted values
        predicted_values = [mixed_exponential_curve(mus, weights, pos) for pos in self.positions]

        # Calculate R-squared
        ss_total = np.sum((self.values - np.mean(self.values))**2)
        ss_residual = np.sum((self.values - np.array(predicted_values))**2)
        r_squared = 1 - (ss_residual / ss_total)

        return mus.tolist(), weights.tolist(), r_squared

    def fit_mbbefd(self) -> Tuple[float, float]:
        """
        Fit an MBBEFD curve to the observed data.

        The MBBEFD curve is parameterized by a c-value.

        Returns:
            Tuple containing:
                - c parameter
                - R-squared value of the fit
        """
        def objective_function(params):
            c_value = params[0]
            predicted_values = [mbbefd_curve(c_value, pos) for pos in self.positions]
            return np.sum((np.array(predicted_values) - self.values)**2)

        # Initial guess for parameter
        initial_guess = [2.0]  # Middle of the typical range

        # Bounds for parameter (c > 0)
        bounds = [(0.5, 10)]

        # Optimize to find the best parameter
        result = optimize.minimize(objective_function, initial_guess, bounds=bounds, method='L-BFGS-B')

        if not result.success:
            raise RuntimeError(f"Optimization failed: {result.message}")

        c_value = result.x[0]

        # Calculate predicted values
        predicted_values = [mbbefd_curve(c_value, pos) for pos in self.positions]

        # Calculate R-squared
        ss_total = np.sum((self.values - np.mean(self.values))**2)
        ss_residual = np.sum((self.values - np.array(predicted_values))**2)
        r_squared = 1 - (ss_residual / ss_total)

        return c_value, r_squared

    def fit_all_curves(self) -> Dict[str, Tuple]:
        """
        Fit all supported curve types and return the results.

        Returns:
            Dictionary mapping curve types to their fitted parameters and R-squared values
        """
        results = {}

        try:
            results['RIEBESELL'] = self.fit_riebesell()
        except Exception as e:
            print(f"Riebesell fitting failed: {e}")

        try:
            results['MIXED_EXPONENTIAL'] = self.fit_mixed_exponential()
        except Exception as e:
            print(f"Mixed exponential fitting failed: {e}")

        try:
            results['MBBEFD'] = self.fit_mbbefd()
        except Exception as e:
            print(f"MBBEFD fitting failed: {e}")

        return results

    def plot_fits(self, riebesell_params=None, mixed_expo_params=None, mbbefd_params=None, title="Exposure Curve Fitting"):
        """
        Plot the observed values and fitted curves.

        Args:
            riebesell_params: Tuple of (z parameter, R-squared) from fit_riebesell
            mixed_expo_params: Tuple of (mus, weights, R-squared) from fit_mixed_exponential
            mbbefd_params: Tuple of (c parameter, R-squared) from fit_mbbefd
            title: Plot title
        """
        plt.figure(figsize=(10, 6))

        # Plot observed values
        plt.scatter(self.positions, self.values, color='black', label='Observed Values')

        # Create a range of positions for smooth curves
        x = np.linspace(0, 1, 100)

        # Plot Riebesell curve if parameters provided
        if riebesell_params:
            z_value, r_squared = riebesell_params
            y_riebesell = [riebesell_curve(0, pos, z_value, self.base_value) for pos in x]
            plt.plot(x, y_riebesell, 'r-', label=f'Riebesell (z={z_value:.3f}, R²={r_squared:.3f})')

        # Plot Mixed Exponential curve if parameters provided
        if mixed_expo_params:
            mus, weights, r_squared = mixed_expo_params
            y_mixed_expo = [mixed_exponential_curve(mus, weights, pos) for pos in x]
            plt.plot(x, y_mixed_expo, 'g-', label=f'Mixed Exponential (R²={r_squared:.3f})')

        # Plot MBBEFD curve if parameters provided
        if mbbefd_params:
            c_value, r_squared = mbbefd_params
            y_mbbefd = [mbbefd_curve(c_value, pos) for pos in x]
            plt.plot(x, y_mbbefd, 'b-', label=f'MBBEFD (c={c_value:.3f}, R²={r_squared:.3f})')

        plt.xlabel('Position')
        plt.ylabel('Value')
        plt.title(title)
        plt.legend()
        plt.grid(True)

        return plt.gcf()  # Return the figure for further customization or saving

def fit_exposure_curve_from_data(positions: List[float], values: List[float]) -> ExposureCurveFitter:
    """
    Fit exposure curves directly from position-value data.

    Args:
        positions: List of relative positions on the curve (typically normalized to [0,1])
        values: List of observed curve values corresponding to the positions

    Returns:
        ExposureCurveFitter object with the data
    """
    return ExposureCurveFitter(positions, values)

def generate_exposure_curve_parameters(curve_type: ExposureCurveType, data: List[Tuple[float, float]]) -> Dict:
    """
    Generate parameters for an exposure curve based on data points.

    Args:
        curve_type: Type of curve to fit
        data: List of (position, value) tuples

    Returns:
        Dictionary of parameters suitable for use with exposure_curve_calculation
    """
    positions, values = zip(*data)
    fitter = ExposureCurveFitter(positions, values)

    if curve_type == ExposureCurveType.RIEBESELL:
        z_value, _ = fitter.fit_riebesell()
        return {"z_value": z_value, "base_limit": 1.0}

    elif curve_type == ExposureCurveType.MIXED_EXPONENTIAL:
        mus, weights, _ = fitter.fit_mixed_exponential()
        return {"paramaters_mus": mus, "parameter_weights": weights}

    elif curve_type == ExposureCurveType.MBBEFD:
        c_value, _ = fitter.fit_mbbefd()
        return {"curve": c_value}

    else:
        raise ValueError(f"Unsupported curve type: {curve_type}")

def select_best_curve(positions: List[float], values: List[float]) -> Tuple[ExposureCurveType, Dict, float]:
    """
    Select the best fitting curve based on R-squared values.

    Args:
        positions: List of relative positions on the curve
        values: List of observed curve values

    Returns:
        Tuple containing:
            - Best curve type
            - Parameters for the best curve
            - R-squared value of the best fit
    """
    fitter = ExposureCurveFitter(positions, values)
    results = fitter.fit_all_curves()

    # Find the curve with the highest R-squared
    best_curve = None
    best_params = None
    best_r_squared = -1

    for curve_type, params in results.items():
        r_squared = params[-1]  # R-squared is the last element in the tuple

        if r_squared > best_r_squared:
            best_r_squared = r_squared
            best_curve = curve_type
            best_params = params

    if best_curve is None:
        raise ValueError("No curves could be fitted successfully")

    # Convert the curve type string to enum
    curve_type_enum = getattr(ExposureCurveType, best_curve)

    # Format parameters for use with exposure_curve_calculation
    if best_curve == 'RIEBESELL':
        params_dict = {"z_value": best_params[0], "base_limit": 1.0}
    elif best_curve == 'MIXED_EXPONENTIAL':
        params_dict = {"paramaters_mus": best_params[0], "parameter_weights": best_params[1]}
    elif best_curve == 'MBBEFD':
        params_dict = {"curve": best_params[0]}

    return curve_type_enum, params_dict, best_r_squared
