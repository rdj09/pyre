"""
Rate Adequacy Calculation Functions

Implements rate adequacy calculations as described in:
Bodoff, N. (2009). "Measuring Rate Change: Methods and Implications."
https://www.casact.org/sites/default/files/database/forum_09wforum_bodoff.pdf
"""

def rate_adequacy(premium: float, indicated_premium: float) -> float:
    """
    Calculates rate adequacy as the ratio of actual premium to indicated premium.

    Args:
        premium (float): Actual charged premium.
        indicated_premium (float): Indicated (actuarially adequate) premium.

    Returns:
        float: Rate adequacy (e.g., 1.05 means 5% adequate, 0.95 means 5% inadequate).
    """
    if indicated_premium == 0:
        raise ValueError("Indicated premium cannot be zero.")
    return premium / indicated_premium

def rate_adequacy_change(
    prior_premium: float,
    prior_indicated: float,
    current_premium: float,
    current_indicated: float
) -> float:
    """
    Calculates the change in rate adequacy between two periods.

    Args:
        prior_premium (float): Actual premium in prior period.
        prior_indicated (float): Indicated premium in prior period.
        current_premium (float): Actual premium in current period.
        current_indicated (float): Indicated premium in current period.

    Returns:
        float: Change in rate adequacy (e.g., 0.05 means 5% improvement).
    """
    prior_adequacy = rate_adequacy(prior_premium, prior_indicated)
    current_adequacy = rate_adequacy(current_premium, current_indicated)
    return current_adequacy - prior_adequacy
