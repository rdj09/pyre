"""
Rate Change Metrics Calculation Module

Bodoff, N. (2009). "Measuring Rate Change: Methods and Implications."
https://www.casact.org/sites/default/files/database/forum_09wforum_bodoff.pdf

Llloyd's PMDR requirements and calculations

https://assets.lloyds.com/media/04e08389-5b68-42a7-aa66-167df72c0721/PMDR-Instructions-2024-V1.0.pdf
https://assets.lloyds.com/assets/pdf-performance-management-pmdr-renewal-scenario-examples/1/pdf-performance-management-PMDR-Renewal-Scenario-Examples.pdf


"""

def rate_change_simple(expiring_premium: float, renewed_premium: float) -> float:
    """
    Calculate simple rate change (no adjustment for exposure or terms).

    Args:
        expiring_premium (float): Premium charged last year.
        renewed_premium (float): Premium charged this year.

    Returns:
        float: Rate change as a decimal (e.g., 0.10 for 10%).
    """
    if expiring_premium == 0:
        raise ValueError("Expiring premium cannot be zero.")
    return (renewed_premium / expiring_premium) - 1

def rate_change_adjusted(
    expiring_premium: float,
    renewed_premium: float,
    adjusted_expiring_premium: Optional[float] = None
) -> float:
    """
    Calculate rate change, optionally adjusting expiring premium for exposure/terms.

    Args:
        expiring_premium (float): Premium charged last year.
        renewed_premium (float): Premium charged this year.
        adjusted_expiring_premium (Optional[float]): Expiring premium adjusted for exposure/terms.

    Returns:
        float: Rate change as a decimal.
    """
    base = adjusted_expiring_premium if adjusted_expiring_premium is not None else expiring_premium
    if base == 0:
        raise ValueError("Expiring or adjusted expiring premium cannot be zero.")
    return (renewed_premium / base) - 1