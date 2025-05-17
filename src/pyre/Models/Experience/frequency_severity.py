from ..models import Model


class severity_fit:
    def __init__(self, data, ground_up:bool = True):
        self.data = data
        self.ground_up_model = ground_up

class frequency_fit:
    def __init__(self, data, ground_up:bool = True):
        self.data = data
        self.ground_up_model = ground_up


class FreqSevModel(Model):
    def __init__(self, data):
        self.data = data

    def frequency_per_unit_exposure():
        pass
    
    def frequency_statistics():
        pass
    
    def average_cost_of_claim():
        pass
    
    def average_claim_cost_statitiscs():
        pass

    #fitting routine NegBin/Poi
    # needs individual developed losses and exposre
    def fit_freq():
        pass

    #fitting routine LogNorm/Pareto/Gamma etc
    # needs indiviudal developed losses as input
    def fit_sev():
        pass