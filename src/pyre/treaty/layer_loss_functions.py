from ..treaty.contract_types import ContractType


def xol_calculation(gross_amount: float, attachment: float, limit: float):
    return max(min(gross_amount - attachment, limit), 0)


def qs_calculation(gross_amount: float, cession: float):
    return max(gross_amount * cession, 0)


def franchise_calculation(gross_amount: float, attachment: float, limit: float):
    if gross_amount > attachment:
        return min(gross_amount, limit)
    else:
        return 0.0


def surplus_share_calculation(
    gross_amount: float, sum_insured: float, retained_line: float, surplus_limit: float
):
    if sum_insured <= 0:
        return 0.0
    surplus_over_retention = max(sum_insured - retained_line, 0.0)
    ceded_portion = min(surplus_over_retention, surplus_limit)
    return (ceded_portion / sum_insured) * gross_amount


layer_loss_calculation = {
    ContractType.QUOTA_SHARE: qs_calculation,
    ContractType.FRANCHISE_DEDUCTIBLE: franchise_calculation,
    ContractType.EXCESS_OF_LOSS: xol_calculation,
    ContractType.AGGREGATE_STOP_LOSS: xol_calculation,
    ContractType.SURPLUS_SHARE: surplus_share_calculation,
}
