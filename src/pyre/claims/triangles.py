from typing import List, Dict
import pandas as pd
from pyre.claims.claims import AggregateClaims

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
