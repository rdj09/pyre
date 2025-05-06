from ..models import Model

class ExperienceModel(Model):
    def __init__(self, data):
        self.data = data



def chainladder_method(data: float, development_factor: float) -> float:
    return data*development_factor

def bf_method(data: float, exposure:float, development_factor: float, a_priori:float):
    return data + (1 - (1/development_factor))*a_priori*exposure

#citation source Lyons, G., Forster, W., Kedney, P., Warren, R., & Wilkinson, H. (n.d.). Claims Reserving Working Party Paper.
# https://www.actuaries.org.uk/documents/claims-reserving-working-party-paper
def cape_cod_method():
        # determine expected loss ratio 
    #bf_method(derived_expected)
    return NotImplementedError


#citation source Lyons, G., Forster, W., Kedney, P., Warren, R., & Wilkinson, H. (n.d.). Claims Reserving Working Party Paper.
# https://www.actuaries.org.uk/documents/claims-reserving-working-party-paper
def generalised_cape_cod_method():
    # determine expected loss ratio with decay factor
    #bf_method(derived_expected)
    return NotImplementedError