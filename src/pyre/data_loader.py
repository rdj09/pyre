import sqlite3
import pandas as pd

#need to make generic loading interface classes for different data sources
# e.g. csv, excel, sql, and other data types of value panquet?

def load_from_excel(file_path, sheet_name=0):
    return pd.read_excel(file_path, sheet_name=sheet_name)

def load_from_sql(db_path, query):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)
    
def from_dataframe(df: pd.DataFrame) :
    # for idx, row in df.iterrows():
    #  try: 
    #  except Exception as e:
    #      raise ValueError(f"Error processing row {idx}: {e}")
    pass