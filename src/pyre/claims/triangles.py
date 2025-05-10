from typing import List, Dict
import pandas as pd
from pyre.claims.claims_aggregator import ClaimAggregator 

class TriangleExporter:
    """_summary_

    Returns:
        _type_: _description_
    """
    @staticmethod
    def export_paid(aggregates: List[AggregateClaims], cumulative: bool = False) -> pd.DataFrame:
        """_summary_

        Args:
            aggregates (List[AggregateClaims]): _description_
            cumulative (bool, optional): _description_. Defaults to False.

        Returns:
            pd.DataFrame: _description_
        """
        data: Dict[int, Dict[int, float]] = {}

        for agg in aggregates:
            for month, paid in enumerate(agg.dev_paid):
                if month not in data:
                    data[month] = {}

                if cumulative:
                    cumulative_paid = sum(agg.dev_paid[:month + 1])
                    data[month][agg.year] = cumulative_paid
                else:
                    data[month][agg.year] = paid

        triangle_df = pd.DataFrame(data).fillna(0)

        triangle_df = triangle_df.sort_index(axis=0)

        return triangle_df

    @staticmethod
    def export_incurred(aggregates: List[AggregateClaims], cumulative: bool = False) -> pd.DataFrame:
        """_summary_

        Args:
            aggregates (List[AggregateClaims]): _description_
            cumulative (bool, optional): _description_. Defaults to False.

        Returns:
            pd.DataFrame: _description_
        """
        data: Dict[int, Dict[int, float]] = {}

        for agg in aggregates:
            for month, incurred in enumerate(agg.dev_incurred):
                if month not in data:
                    data[month] = {}

                if cumulative:
                    cumulative_incurred = sum(agg.dev_incurred[:month + 1])
                    data[month][agg.year] = cumulative_incurred
                else:
                    data[month][agg.year] = incurred

        triangle_df = pd.DataFrame(data).fillna(0)

        triangle_df = triangle_df.sort_index(axis=0)

        return triangle_df


#TODO IBNER methodology citation of source SCHNIEPER https://www.casact.org/sites/default/files/database/astin_vol21no1_111.pdf
# need to review below

class IBNERPatternExtractor:
    def __init__(self, claim_aggregators: List[ClaimAggregator]):
        """
        Initialize with a list of ClaimAggregator objects.

        Args:
            claim_aggregators (List[ClaimAggregator]): List of ClaimAggregator instances containing cumulative claims data.
        """
        self.claim_aggregators = claim_aggregators
        self.accident_years = sorted(set(agg.accident_year for agg in claim_aggregators))
        self.development_years = sorted(set(dev for agg in claim_aggregators for dev in range(len(agg.cumulative_incurred))))
        self.N = {ay: {} for ay in self.accident_years}
        self.D = {ay: {} for ay in self.accident_years}
        self._compute_N_and_D()

    def _compute_N_and_D(self):
        """
        Compute the N and D triangles from cumulative data in ClaimAggregator.
        """
        for agg in self.claim_aggregators:
            ay = agg.accident_year
            cumulative_incurred = agg.cumulative_incurred

            for idx, dy in enumerate(self.development_years):
                if idx >= len(cumulative_incurred):
                    self.N[ay][dy] = None
                    self.D[ay][dy] = None
                    continue

                current = cumulative_incurred[idx]
                if idx == 0:
                    self.N[ay][dy] = current
                    self.D[ay][dy] = None
                else:
                    prev = cumulative_incurred[idx - 1]

                    if current is None or prev is None:
                        self.N[ay][dy] = None
                        self.D[ay][dy] = None
                    else:
                        self.D[ay][dy] = prev - current
                        self.N[ay][dy] = current - prev + self.D[ay][dy]

    def get_N_triangle(self) -> Dict[int, Dict[int, float]]:
        """
        Returns the N triangle (new claims).

        Returns:
            Dict[int, Dict[int, float]]: N triangle with accident years as keys and development years as sub-keys.
        """
        return self.N

    def get_D_triangle(self) -> Dict[int, Dict[int, float]]:
        """
        Returns the D triangle (IBNER development).

        Returns:
            Dict[int, Dict[int, float]]: D triangle with accident years as keys and development years as sub-keys.
        """
        return self.D

    def get_IBNER_pattern(self) -> Dict[int, float]:
        """
        Returns the average D (IBNER) pattern per development year.

        Returns:
            Dict[int, float]: Dictionary with development year as key and average IBNER as value.
        """
        sums = {dy: 0.0 for dy in self.development_years}
        counts = {dy: 0 for dy in self.development_years}

        for ay in self.accident_years:
            for dy in self.development_years:
                val = self.D.get(ay, {}).get(dy)
                if val is not None:
                    sums[dy] += val
                    counts[dy] += 1

        return {dy: (sums[dy] / counts[dy]) if counts[dy] > 0 else None for dy in self.development_years}