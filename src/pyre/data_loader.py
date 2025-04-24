import sqlite3
from typing import List
import pandas as pd
from datetime import date
from pyre.exposures.exposures import Exposure, AggregateExposure, ExposureType

def load_from_excel(file_path, sheet_name=0):
    return pd.read_excel(file_path, sheet_name=sheet_name)

def load_from_sql(db_path, query):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)
    
class ExposureLoader:
    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> List[Exposure]:
        exposures = []

        for idx, row in df.iterrows():
            try:
                exposure = Exposure(
                    exposure_id=str(row["exposure_id"]),
                    insured_value=float(row["insured_value"]),
                    attachment_point=float(row["attachment_point"]),
                    limit=float(row["limit"]),
                    deductible=float(row["deductible"]),
                    policy_start=pd.to_datetime(row["policy_start"]).date(),
                    policy_end=pd.to_datetime(row["policy_end"]).date(),
                    location=row.get("location"),
                    peril=row.get("peril"),
                    occupancy=row.get("occupancy"),
                    aggregate=bool(row.get("aggregate", False)),
                    exposure_type=ExposureType(row["exposure_type"].lower())
                )
                exposures.append(exposure)
            except Exception as e:
                raise ValueError(f"Error processing row {idx}: {e}")

        return exposures

    @staticmethod
    def to_aggregate_exposure(exposures: List[Exposure]) -> AggregateExposure:
        agg = AggregateExposure()
        for exp in exposures:
            agg.add_exposure(exp)
        return agg