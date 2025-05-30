from enum import Enum

class ContractType(Enum):
    QUOTA_SHARE = "Quota Share"
    EXCESS_OF_LOSS = "Excess of Loss"
    FRANCHISE_DEDUCTIBLE = "Franchise Deductible"
    SURPLUS_SHARE = "Surplus Share"
    AGGREGATE_STOP_LOSS = "Aggregate Stop Loss"