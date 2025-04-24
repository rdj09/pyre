from typing import List, Dict
import pandas as pd
from claims import AggregateClaims

class TriangleExporter:
    @staticmethod
    def export_paid(aggregates: List[AggregateClaims], cumulative: bool = False) -> pd.DataFrame:
        """Export the paid data into a triangle format, optionally cumulative."""
        # Create a dictionary to store the data by development month and accident year
        data: Dict[int, Dict[int, float]] = {}

        # Iterate over each aggregate claim to populate the triangle
        for agg in aggregates:
            for month, paid in enumerate(agg.dev_paid):
                if month not in data:
                    data[month] = {}

                # If cumulative is True, sum the paid values up to the current month
                if cumulative:
                    cumulative_paid = sum(agg.dev_paid[:month + 1])
                    data[month][agg.year] = cumulative_paid
                else:
                    data[month][agg.year] = paid

        # Convert the data dictionary into a DataFrame
        triangle_df = pd.DataFrame(data).fillna(0)

        # Reorder rows (development months) in ascending order
        triangle_df = triangle_df.sort_index(axis=0)

        return triangle_df

    @staticmethod
    def export_incurred(aggregates: List[AggregateClaims], cumulative: bool = False) -> pd.DataFrame:
        """Export the incurred data into a triangle format, optionally cumulative."""
        # Create a dictionary to store the data by development month and accident year
        data: Dict[int, Dict[int, float]] = {}

        # Iterate over each aggregate claim to populate the triangle
        for agg in aggregates:
            for month, incurred in enumerate(agg.dev_incurred):
                if month not in data:
                    data[month] = {}

                # If cumulative is True, sum the incurred values up to the current month
                if cumulative:
                    cumulative_incurred = sum(agg.dev_incurred[:month + 1])
                    data[month][agg.year] = cumulative_incurred
                else:
                    data[month][agg.year] = incurred

        # Convert the data dictionary into a DataFrame
        triangle_df = pd.DataFrame(data).fillna(0)

        # Reorder rows (development months) in ascending order
        triangle_df = triangle_df.sort_index(axis=0)

        return triangle_df
        


