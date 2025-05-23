from typing import Dict, List, Optional
from pyre.claims.claims import Claims

class Triangle:
    """
    Represents a triangle of claim values (e.g., paid or incurred) by origin (modelling) year and development period.
    """

    def __init__(
        self,
        triangle: Optional[Dict[int, Dict[int, float]]] = None,
        origin_years: Optional[List[int]] = None,
        dev_periods: Optional[List[int]] = None,
    ):
        """
        Initialize a Triangle directly or as an empty structure.
        """
        self.triangle = triangle if triangle is not None else {}
        self.origin_years = origin_years if origin_years is not None else []
        self.dev_periods = dev_periods if dev_periods is not None else []

    @classmethod
    def from_claims(cls, claims: Claims, value_type: str = "incurred") -> "Triangle":
        """
        Construct a Triangle from a Claims object.
        value_type: "incurred" or "paid"
        """
        # Collect all unique modelling years and max development length
        origin_years = claims.modelling_years
        dev_periods = claims.development_periods

        # Build the triangle
        triangle = {year: {} for year in origin_years}
        for claim in claims:
            #TODO aggregation 
            # claim.capped_claim_development_history.cumulative_dev_paid # paid
            # claim.capped_claim_development_history.cumulative_dev_incurred # incurred
            ... #TODO aggregation of claims data by modelling years

        return cls(triangle=triangle, origin_years=origin_years, dev_periods=dev_periods)
    

#TODO IBNER methodology citation of source SCHNIEPER https://www.casact.org/sites/default/files/database/astin_vol21no1_111.pdf
class IBNERPatternExtractor:
    """
    Extracts IBNER patterns from either a Claims object or a Triangle object.
    """
    def __init__(self, triangle: Triangle):
        self.triangle = triangle.triangle
        self.origin_years = triangle.origin_years
        self.dev_periods = triangle.dev_periods

        self.N = {oy: {} for oy in self.origin_years}
        self.D = {oy: {} for oy in self.origin_years}
        self._compute_N_and_D()

    def _compute_N_and_D(self):
        """
        Compute the N and D triangles from cumulative data.
        """
        for oy in self.origin_years:
            cumulative = [self.triangle[oy].get(d, None) for d in self.dev_periods]
            for idx, d in enumerate(self.dev_periods):
                if idx >= len(cumulative) or cumulative[idx] is None:
                    self.N[oy][d] = None
                    self.D[oy][d] = None
                    continue

                current = cumulative[idx]
                if idx == 0:
                    self.N[oy][d] = current
                    self.D[oy][d] = None
                else:
                    prev = cumulative[idx - 1]
                    if current is None or prev is None:
                        self.N[oy][d] = None
                        self.D[oy][d] = None
                    else:
                        self.D[oy][d] = prev - current
                        self.N[oy][d] = current - prev + self.D[oy][d]

    def get_N_triangle(self) -> Dict[int, Dict[int, float]]:
        """
        Returns the N triangle (new claims).
        """
        return self.N

    def get_D_triangle(self) -> Dict[int, Dict[int, float]]:
        """
        Returns the D triangle (IBNER development).
        """
        return self.D

    def get_IBNER_pattern(self) -> Dict[int, float]:
        """
        Returns the average D (IBNER) pattern per development year.
        """
        sums = {d: 0.0 for d in self.dev_periods}
        counts = {d: 0 for d in self.dev_periods}

        for oy in self.origin_years:
            for d in self.dev_periods:
                val = self.D.get(oy, {}).get(d)
                if val is not None:
                    sums[d] += val
                    counts[d] += 1

        return {d: (sums[d] / counts[d]) if counts[d] > 0 else None for d in self.dev_periods}