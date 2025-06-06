
# Implementation of ILF fitting methods based on:
# "Increased Limits Ratemaking for Liability Insurance" by Palmer (CAS Study Note)
# https://www.casact.org/sites/default/files/database/studynotes_palmer.pdf

import numpy as np
from scipy import optimize
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional, Union, Callable
from .exposure_ILF_functions import pareto_ilf, power_ilf, pareto_limited_severity

class ILFFitter:
    """
    Class for fitting Increased Limit Factors (ILFs) using various methods.

    This class implements the methods described in the Palmer paper for fitting ILFs,
    including empirical fitting, curve fitting, and distribution fitting.
    """

    def __init__(self, limits: List[float], ilfs: List[float], base_limit: float):
        """
        Initialize the ILF fitter with observed limits and ILFs.

        Args:
            limits: List of policy limits
            ilfs: List of observed ILFs corresponding to the limits
            base_limit: The base limit used for the ILFs
        """
        self.limits = np.array(limits)
        self.ilfs = np.array(ilfs)
        self.base_limit = base_limit

        # Validate inputs
        if len(self.limits) != len(self.ilfs):
            raise ValueError("Limits and ILFs must have the same length")
        if not all(x > 0 for x in self.limits):
            raise ValueError("All limits must be positive")
        if not all(x > 0 for x in self.ilfs):
            raise ValueError("All ILFs must be positive")
        if self.base_limit <= 0:
            raise ValueError("Base limit must be positive")

    def fit_power_curve(self) -> Tuple[float, float]:
        """
        Fit a power curve to the observed ILFs.

        The power curve has the form: ILF = (limit/base_limit)^p

        Returns:
            Tuple containing:
                - power parameter (p)
                - R-squared value of the fit
        """
        # Take logarithms to linearize the power function
        log_limits_ratio = np.log(self.limits / self.base_limit)
        log_ilfs = np.log(self.ilfs)

        # Fit a linear regression to the log-transformed data
        # The slope of this line is the power parameter
        slope, _ = np.polyfit(log_limits_ratio, log_ilfs, 1)

        # Calculate predicted values
        predicted_ilfs = power_ilf(self.limits, self.base_limit, slope)

        # Calculate R-squared
        ss_total = np.sum((self.ilfs - np.mean(self.ilfs))**2)
        ss_residual = np.sum((self.ilfs - predicted_ilfs)**2)
        r_squared = 1 - (ss_residual / ss_total)

        return slope, r_squared

    def fit_pareto(self) -> Tuple[float, float, float]:
        """
        Fit a Pareto distribution to the observed ILFs.

        The Pareto distribution has the form:
        ILF(limit) = [1 - (alpha / (alpha + limit/scale))^(alpha-1)] / 
                     [1 - (alpha / (alpha + base_limit/scale))^(alpha-1)]

        Returns:
            Tuple containing:
                - alpha parameter
                - scale parameter (x_m)
                - R-squared value of the fit
        """
        def objective_function(params):
            alpha, x_m = params
            predicted_ilfs = [pareto_ilf(self.base_limit, limit, alpha, x_m) for limit in self.limits]
            return np.sum((np.array(predicted_ilfs) - self.ilfs)**2)

        # Initial guess for parameters
        initial_guess = [2.0, self.base_limit / 10]

        # Bounds for parameters (alpha > 1, x_m > 0)
        bounds = [(1.001, 10), (0.001, self.base_limit)]

        # Optimize to find the best parameters
        result = optimize.minimize(objective_function, initial_guess, bounds=bounds, method='L-BFGS-B')

        if not result.success:
            raise RuntimeError(f"Optimization failed: {result.message}")

        alpha, x_m = result.x

        # Calculate predicted values
        predicted_ilfs = [pareto_ilf(self.base_limit, limit, alpha, x_m) for limit in self.limits]

        # Calculate R-squared
        ss_total = np.sum((self.ilfs - np.mean(self.ilfs))**2)
        ss_residual = np.sum((self.ilfs - np.array(predicted_ilfs))**2)
        r_squared = 1 - (ss_residual / ss_total)

        return alpha, x_m, r_squared

    def fit_empirical(self) -> Dict[float, float]:
        """
        Create an empirical ILF table from the observed data.

        Returns:
            Dictionary mapping limits to ILFs
        """
        return dict(zip(self.limits, self.ilfs))

    def plot_fits(self, power_params=None, pareto_params=None, title="ILF Curve Fitting"):
        """
        Plot the observed ILFs and fitted curves.

        Args:
            power_params: Tuple of (power parameter, R-squared) from fit_power_curve
            pareto_params: Tuple of (alpha, x_m, R-squared) from fit_pareto
            title: Plot title
        """
        plt.figure(figsize=(10, 6))

        # Plot observed ILFs
        plt.scatter(self.limits, self.ilfs, color='black', label='Observed ILFs')

        # Create a range of limits for smooth curves
        x = np.linspace(self.base_limit, max(self.limits) * 1.1, 100)

        # Plot power curve if parameters provided
        if power_params:
            power_param, r_squared = power_params
            y_power = power_ilf(x, self.base_limit, power_param)
            plt.plot(x, y_power, 'r-', label=f'Power Curve (p={power_param:.3f}, R²={r_squared:.3f})')

        # Plot Pareto curve if parameters provided
        if pareto_params:
            alpha, x_m, r_squared = pareto_params
            y_pareto = [pareto_ilf(self.base_limit, limit, alpha, x_m) for limit in x]
            plt.plot(x, y_pareto, 'b-', label=f'Pareto (α={alpha:.3f}, x_m={x_m:.3f}, R²={r_squared:.3f})')

        plt.xlabel('Limit')
        plt.ylabel('ILF')
        plt.title(title)
        plt.legend()
        plt.grid(True)

        return plt.gcf()  # Return the figure for further customization or saving

def fit_ilf_from_losses(losses: List[float], limits: List[float], base_limit: float) -> ILFFitter:
    """
    Fit ILFs directly from loss data.

    Args:
        losses: List of individual losses
        limits: List of limits to calculate ILFs for
        base_limit: Base limit for ILF calculation

    Returns:
        ILFFitter object with fitted parameters
    """
    # Calculate empirical limited average severity for each limit
    limited_losses = {}
    for limit in [base_limit] + limits:
        limited_losses[limit] = np.mean([min(loss, limit) for loss in losses])

    # Calculate ILFs
    ilfs = [limited_losses[limit] / limited_losses[base_limit] for limit in limits]

    # Create and return ILFFitter
    return ILFFitter(limits, ilfs, base_limit)

def fit_ilf_from_severity_curve(severity_function: Callable, limits: List[float], base_limit: float) -> ILFFitter:
    """
    Generate ILFs from a severity curve function.

    Args:
        severity_function: Function that takes a limit and returns the limited expected value
        limits: List of limits to calculate ILFs for
        base_limit: Base limit for ILF calculation

    Returns:
        ILFFitter object with generated ILFs
    """
    # Calculate limited expected values
    base_lev = severity_function(base_limit)
    ilfs = [severity_function(limit) / base_lev for limit in limits]

    # Create and return ILFFitter
    return ILFFitter(limits, ilfs, base_limit)

def calculate_ilf_table(alpha: float, x_m: float, base_limit: float, limits: List[float]) -> pd.DataFrame:
    """
    Calculate an ILF table using the Pareto distribution.

    Args:
        alpha: Pareto alpha parameter
        x_m: Pareto scale parameter
        base_limit: Base limit for ILF calculation
        limits: List of limits to calculate ILFs for

    Returns:
        DataFrame with limits and corresponding ILFs
    """
    ilfs = [pareto_ilf(base_limit, limit, alpha, x_m) for limit in limits]
    return pd.DataFrame({'Limit': limits, 'ILF': ilfs})
