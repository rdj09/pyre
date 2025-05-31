from pyre.treaty.contract_types import ContractType


def xol_calculation(gross_amount: float, attachment: float, limit: float):
    return max(min(gross_amount - attachment,limit),0)

def qs_calculation(gross_amount:float, cession:float):
    return max(gross_amount * cession,0)

def franchise_calculation(    gross_amount: float, attachment: float, limit: float):
    if gross_amount > attachment:
        return min(gross_amount,limit)
    else: 
        return 0.0

def surplus_share_calculation(gross_amount: float, sum_insured:float, attachment:float):
    if sum_insured <= attachment:
        return 0.0  # No ceded amount if the sum insured is within the retention
    surplus = sum_insured - attachment
    share = surplus / sum_insured
    return share * gross_amount

layer_loss_calculation = {
    ContractType.QUOTA_SHARE: qs_calculation,
    ContractType.FRANCHISE_DEDUCTIBLE: franchise_calculation,
    ContractType.EXCESS_OF_LOSS: xol_calculation,
    ContractType.AGGREGATE_STOP_LOSS: xol_calculation,
    ContractType.SURPLUS_SHARE: surplus_share_calculation
    }
