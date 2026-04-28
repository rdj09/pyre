import random

from ...claims.claims import Claim
from ...models.experience.experience_preparer import ExperienceModelData


class Resampling:
    """Resamples claims data from an ExperienceModelData object for bootstrapping."""

    def __init__(self, model_data: ExperienceModelData, random_seed: int | None = None) -> None:
        self._claims = model_data.trended_claims
        self._rng = random.Random(random_seed)

    def resample(self) -> Claim:
        """Return a randomly selected claim from the trended claims collection."""
        return self._rng.choice(self._claims.claims)
