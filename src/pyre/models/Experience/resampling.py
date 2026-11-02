import random
from typing import List, Optional

from ...models.Experience.experience_preparer import ExperienceModelData
from ...claims.claims import Claim


class resampling():
    """
    A class for resampling claims data from an ExperienceModelData object.

    This class provides functionality to randomly select claims (with replacement)
    from a set of trended claims for the purpose of simulation or bootstrapping
    analysis, following the nonparametric bootstrap of Efron & Tibshirani (1993),
    "An Introduction to the Bootstrap", Chapter 2: a resampled claim set is built
    by drawing n claims uniformly at random, with replacement, from the observed
    (trended) claims pool.

    Attributes:
        _claims: A collection of trended claims from the ExperienceModelData object.
                These are claims that have been adjusted to the contract inception year.

    Note:
        Support for "different return periods" (i.e. deriving a return-period-based
        loss distribution from repeated resamples) remains deferred -- it is
        under-specified (no agreed definition of how a single resample's result
        maps to a return period) and is intentionally out of scope here.
    """
    def __init__(self, claims: ExperienceModelData) -> None:
        """
        Initialize the resampling class with claims data.

        Parameters:
            claims (ExperienceModelData): An ExperienceModelData object containing the claims
                                         to be resampled. The trended_claims property of this
                                         object will be used for resampling.
        """
        self._claims = claims.trended_claims #trended loss prior to subject losses


    def resample(self, n: int = 1, random_seed: Optional[int] = None) -> List[Claim]:
        """
        Draw a bootstrap resample of n claims, with replacement, from the
        collection of trended claims.

        This implements the nonparametric bootstrap described in Efron &
        Tibshirani (1993), "An Introduction to the Bootstrap", Chapter 2:
        each of the n draws is made independently and uniformly at random
        (with replacement) from the observed claims, so the same claim may
        appear more than once in the result and some claims may not appear
        at all.

        Parameters:
            n (int): The number of claims to draw. Defaults to 1.
            random_seed (Optional[int]): Seed for the random number generator,
                to make the resample reproducible. If None, the shared
                `random` module state is used (non-reproducible).

        Returns:
            List[Claim]: A list of n claims drawn with replacement from the
                trended claims pool.

        Note:
            Support for "different return periods" remains deferred -- see the
            class docstring -- and is not implemented by this method.
        """
        rng = random.Random(random_seed) if random_seed is not None else random
        return rng.choices(self._claims.claims, k=n)
