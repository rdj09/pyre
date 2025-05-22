from collections import namedtuple
from pyre.treaty.contracts import RIContract

#TODO tidy up and consider refactor and seperate processes 
modelling_assumptions = namedtuple("ModellingAssumptions",["cost_of_capital","required_rate_of_return"])
assumptions = modelling_assumptions(cost_of_capital=0.3,required_rate_of_return=0.1 )

class AggregateFeatures:
    def __init__(self, subject_contract: RIContract, assumptions_inputs: tuple) -> None:
        self._subject_contract = subject_contract
        self._assumptions_inputs = assumptions_inputs
    