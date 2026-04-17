from random import choice

from ...claims.claims import Claim
from ...models.experience.experience_preparer import ExperienceModelData


class Resampling:
    """Resamples claims data from an ExperienceModelData object for bootstrapping."""

    def __init__(self, claims: ExperienceModelData) -> None:
        self._claims = claims.trended_claims

    def resample(self) -> Claim:
        """Return a randomly selected claim from the trended claims collection."""
        return choice(self._claims.claims)
