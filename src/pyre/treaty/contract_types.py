from enum import Enum, auto

class ContractType(Enum):
    QUOTA_SHARE = auto()
    EXCESS_OF_LOSS = auto()
    FRANCHISE_DEDUCTIBLE = auto()
    SURPLUS_SHARE = auto()
    AGGREGATE_STOP_LOSS = auto()