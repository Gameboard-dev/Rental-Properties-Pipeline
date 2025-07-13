import pandas as pd
from scripts.csv_columns import LATITUDE, LONGITUDE
from geopy.distance import great_circle

YEREVAN_CENTRE = (40.1792, 44.4991)

def compute_distance(row: pd.Series) -> float:
    return great_circle((row[LATITUDE], row[LONGITUDE]), YEREVAN_CENTRE).km


