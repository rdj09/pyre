from pyre.claims.claims import Claims
from pyre.exposures.exposures import Exposures

def trended_exposures(self) -> Exposures:
    #TODO apply trend factors to data
    return Exposures(...)
      
def trended_claims(self) -> Claims:
    #TODO #apply trend factors to the data
    return Claims(...) 


#source citation: 
# Deters, I. (2017). The Mathematics of On-Leveling. 
# https://www.casact.org/sites/default/files/database/forum_17spforum_03-deters.pdf
