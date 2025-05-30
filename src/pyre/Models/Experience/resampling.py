from pyre.Models.Experience.experience_preparer import ExperienceModelData 
from random import choice


class resampling()
    def __init__(self, claims: ExperienceModelData) -> None:
        self._claims = ExperienceModelData.trended_claims #trended loss prior to subject losses
        
    
    def resample(self) -> None:
        choice(self._claims)
        # TODO fleshout further return periods etc but iter method of Claims should permit choice to function
        



