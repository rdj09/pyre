from ...Models.Experience.experience_preparer import ExperienceModelData
from random import choice


class resampling():
    """
    A class for resampling claims data from an ExperienceModelData object.

    This class provides functionality to randomly select claims from a set of trended claims
    for the purpose of simulation or bootstrapping analysis. It uses the random.choice function
    to select individual claims from the trended claims data.

    Attributes:
        _claims: A collection of trended claims from the ExperienceModelData object.
                These are claims that have been adjusted to the contract inception year.

    Note:
        Future enhancements planned include support for different return periods and
        more sophisticated resampling methods. The implementation relies on the Claims
        class having an iterator method to work with the random.choice function.
    """
    def __init__(self, claims: ExperienceModelData) -> None:
        """
        Initialize the resampling class with claims data.

        Parameters:
            claims (ExperienceModelData): An ExperienceModelData object containing the claims
                                         to be resampled. The trended_claims property of this
                                         object will be used for resampling.
        """
        self._claims = ExperienceModelData.trended_claims #trended loss prior to subject losses


    def resample(self) -> None:
        """
        Randomly select a claim from the collection of trended claims.

        This method uses the random.choice function to select a single claim
        from the trended claims data. Currently, it doesn't return the selected
        claim but this behavior may change in future implementations.

        Returns:
            None: Currently doesn't return anything, but may be updated to return
                 the selected claim in future implementations.

        Note:
            Future enhancements will include support for different return periods
            and more sophisticated resampling methods.
        """
        choice(self._claims)
        # TODO fleshout further return periods etc but iter method of Claims should permit choice to function
