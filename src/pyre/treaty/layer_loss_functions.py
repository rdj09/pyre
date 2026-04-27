from collections.abc import Callable

from ..enums import ContractType


def xol_calculation(gross_amount: float, attachment: float, limit: float) -> float:
    return max(min(gross_amount - attachment, limit), 0)


def qs_calculation(gross_amount: float, cession: float) -> float:
    return max(gross_amount * cession, 0)


def quota_share_calculation(gross_amount: float, attachment: float, limit: float) -> float:
    """Calculate quota share loss. QS cedes 100% of gross loss."""
    return gross_amount


def franchise_calculation(gross_amount: float, attachment: float, limit: float) -> float:
    if gross_amount > attachment:
        return min(gross_amount, limit)
    else:
        return 0.0


def surplus_share_calculation(gross_amount: float, sum_insured: float, attachment: float) -> float:
    if sum_insured <= attachment:
        return 0.0
    surplus = sum_insured - attachment
    share = surplus / sum_insured
    return share * gross_amount


layer_loss_calculation: dict[ContractType, Callable[[float, float, float], float]] = {
    ContractType.QUOTA_SHARE: quota_share_calculation,
    ContractType.FRANCHISE_DEDUCTIBLE: franchise_calculation,
    ContractType.EXCESS_OF_LOSS: xol_calculation,
    ContractType.AGGREGATE_STOP_LOSS: xol_calculation,
}
