from math import log, exp, sqrt
from typing import List, Tuple

# source citation
# Lyons, G., Forster, W., Kedney, P., Warren, R., & Wilkinson, H. (n.d.). Claims Reserving Working Party Paper.
# https://www.actuaries.org.uk/system/files/documents/pdf/lyons.pdf

def linear_regression(x: List[float], y: List[float]) -> Tuple[float, float]:
    """
    Performs linear regression to calculate the slope and intercept.

    Args:
        x (List[float]): The independent variable values.
        y (List[float]): The dependent variable values.

    Returns:
        Tuple[float, float]: The slope and intercept of the regression line.
    """
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)

    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denominator = sum((xi - mean_x) ** 2 for xi in x)

    slope = numerator / denominator
    intercept = mean_y - slope * mean_x

    return (slope, intercept)


def exponential_fit(age_to_age_factors: List[float], time_periods: List[float]) -> Tuple[float,float]:
    """
    Fits an exponential curve to the given age-to-age factors using the model:
    rj = exp(a + b * t), where ln(rj) = a + b * t.

    Args:
        age_to_age_factors (List[float]): The incremental age-to-age factors (rj).
        time_periods (List[int]): The corresponding time periods (t).

    Returns:
        List[float]: A list containing the parameters [a, b] of the exponential curve.
    """
    ln_rj = [log(rj - 1) for rj in age_to_age_factors]
    b, a = linear_regression(time_periods, ln_rj)
    return (a, b)


def power_fit(age_to_age_factors: List[float], time_periods: List[float]) -> Tuple[float,float]:
    """
    Fits a power curve to the given cumulative age-to-age factors using the model:
    Rj = a * (b^t), where ln(ln(Rj)) = ln(ln(a)) + (ln(b) * t).

    Args:
        age_to_age_factors (List[float]): The cumulative age-to-age factors (Rj).
        time_periods (List[int]): The corresponding time periods (t).

    Returns:
        List[float]: A list containing the parameters [a, b] of the power curve.
    """
    ln_ln_Rj = [log(log(Rj)) for Rj in age_to_age_factors]
    ln_b, ln_ln_a = linear_regression(time_periods, ln_ln_Rj)
    a = exp(exp(ln_ln_a))
    b = exp(ln_b)
    return (a, b)


def weibull_fit(age_to_age_factors: List[float], time_periods: List[float]) -> Tuple[float,float]:
    """
    Fits a Weibull curve to the given cumulative age-to-age factors using the model:
    Rj = 1 / (1 - exp(-a * t^b)).

    Args:
        age_to_age_factors (List[float]): The cumulative age-to-age factors (Rj).
        time_periods (List[int]): The corresponding time periods (t).

    Returns:
        List[float]: A list containing the parameters [a, b] of the Weibull curve.
    """
    transformed_Rj = [log(-log(1 - 1 / Rj)) for Rj in age_to_age_factors]
    ln_t = [log(t) for t in time_periods]
    b, ln_a = linear_regression(ln_t, transformed_Rj)
    a = exp(ln_a)
    return (a, b)


def inverse_power_fit(age_to_age_factors: List[float], time_periods: List[float], c_values: List[float]) -> Tuple[float, float, float]:
    """
    Fits a Sherman Curve (Inverse Power Curve) to the given incremental age-to-age factors using the model:
    rj = a * (t + c)^b.

    Args:
        age_to_age_factors (List[float]): The incremental age-to-age factors (rj).
        time_periods (List[int]): The corresponding time periods (t).
        c_values (List[float]): A list of candidate values for c to test.

    Returns:
        List[float]: A list containing the parameters [a, b, c] of the Sherman Curve.
    """
    def calculate_standard_error(a: float, b: float, c: float) -> float:
        predicted_rj = [a * ((t + c) ** b) for t in time_periods]
        errors = [(rj - pred_rj) ** 2 for rj, pred_rj in zip(age_to_age_factors, predicted_rj)]
        return sqrt(sum(errors) / len(errors))

    best_a, best_b, best_c = 0.0, 0.0, 0.0
    min_standard_error = float('inf')

    for c in c_values:
        ln_rj = [log(rj - 1) for rj in age_to_age_factors]
        ln_t_plus_c = [log(t + c) for t in time_periods]
        b, ln_a = linear_regression(ln_t_plus_c, ln_rj)
        a = exp(ln_a)
        standard_error = calculate_standard_error(a, b, c)

        if standard_error < min_standard_error:
            min_standard_error = standard_error
            best_a, best_b, best_c = a, b, c

    return (best_a, best_b, best_c)


def residuals_standardised(actual: List[float], expected: List[float], num_parameters: int) -> List[float]:
    # Calculate residuals
    residuals = [a - e for a, e in zip(actual, expected)]
    
    # Calculate sigma^2 (variance estimate)
    n = len(actual)
    sigma_squared = sum((a - e) ** 2 for a, e in zip(actual, expected)) / (n - num_parameters)
    sigma = sqrt(sigma_squared)
    
    # Calculate standardized residuals
    standardized_residuals = [residual / sigma for residual in residuals]
    
    return standardized_residuals


def r_squared(actual: List[float], expected: List[float]) -> float:
    """
    Calculates the R-squared (coefficient of determination) value.

    Args:
        actual (List[float]): The actual observed values.
        expected (List[float]): The expected values from the model.

    Returns:
        float: The R-squared value.
    """
    # Calculate the total sum of squares (TSS)
    mean_actual = sum(actual) / len(actual)
    total_sum_of_squares = sum((a - mean_actual) ** 2 for a in actual)

    # Calculate the residual sum of squares (RSS)
    residual_sum_of_squares = sum((a - e) ** 2 for a, e in zip(actual, expected))

    # Calculate R-squared
    r_squared_value = 1 - (residual_sum_of_squares / total_sum_of_squares)

    return r_squared_value

def assess_error_assumptions(actual: List[float], expected: List[float], num_parameters: int) -> dict:
    """
    Assesses the error term based on standardized residuals and calculates:
    - The proportion of positive standardized residuals.
    - The proportion of standardized residuals outside the range (-2, 2).

    Args:
        actual (List[float]): The actual observed values.
        expected (List[float]): The expected values from the model.
        num_parameters (int): The number of parameters in the model.

    Returns:
        dict: A dictionary containing:
            - 'proportion_positive': Proportion of positive standardized residuals.
            - 'proportion_outside_range': Proportion of standardized residuals outside (-2, 2).
            - 'mean_residual': Mean of the standardized residuals.
            - 'std_residual': Standard deviation of the standardized residuals.
    """
    # Calculate standardized residuals
    residuals = residuals_standardised(actual, expected, num_parameters)

    # Proportion of positive standardized residuals
    proportion_positive = sum(1 for r in residuals if r > 0) / len(residuals)

    # Proportion of standardized residuals outside the range (-2, 2)
    proportion_outside_range = sum(1 for r in residuals if r < -2 or r > 2) / len(residuals)

    # Mean and standard deviation of standardized residuals
    mean_residual = sum(residuals) / len(residuals)
    std_residual = sqrt(sum((r - mean_residual) ** 2 for r in residuals) / len(residuals))

    return {
        "proportion_positive": proportion_positive,
        "proportion_outside_range": proportion_outside_range,
        "mean_residual": mean_residual,
        "std_residual": std_residual,
    }

#TODO IBNER methodology citation of source SCHNIEPER https://www.casact.org/sites/default/files/database/astin_vol21no1_111.pdf

def ibner_development():
    pass