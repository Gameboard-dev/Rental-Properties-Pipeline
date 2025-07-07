import json
import logging
from typing import Union
from numpy import ndarray
import pandas as pd
from scripts.csv_columns import *
from settings import ARMENIAN_REGION, FUZZY_MATCH_ACCURACY
from rapidfuzz import process
from settings import FUZZY_MATCH_ACCURACY


def retrieve_armenian_regional_structure() -> tuple[set[str], dict[str, str], dict[str, str]]:
    ''' Retrieves the Armenian regional structured based on Wikipedia '''

    if not ARMENIAN_REGION.exists():
        return set(), {}, {}

    with (ARMENIAN_REGION).open('r', encoding='utf-8') as f:
        regional_structure: dict = json.load(f)

    if regional_structure:

        provinces = set()
        administrative_units_mapping = dict()
        locality_mapping = dict()

        for province, data in regional_structure.items():

            provinces.add(province)

            if isinstance(data, list):
                for d in data:
                    # Yerevan districts
                    administrative_units_mapping[d] = province

            else:
                municipality_data: dict[str, dict[str, dict[str, str]]] = data

                for municipality, localities in municipality_data.items():
                    administrative_units_mapping[municipality] = province

                    for locality in localities: 
                        locality_mapping[locality] = municipality

        return (provinces, administrative_units_mapping, locality_mapping)
    

def fuzzy_match(string: str, choices: set) -> str:
    # Remove commas and use spaces as delimiters
    words = string.title().replace(',', '').split()
    # Try match for each word
    for word in words:
        if word in choices:
            return word
    # Fallback fuzzy match is used
    matches = process.extractOne(string, choices, score_cutoff=FUZZY_MATCH_ACCURACY)
    return matches[0] if matches else ""


def reverse_lookup(name: str, mapping: dict) -> str:
    return mapping.get(name, "")


def administrative_pairs(df: pd.DataFrame) -> list[dict[str, str]]:
    """Returns unique (administrative, province) pairs and logs administrative units with no valid province."""

    df = df[[ADMINISTRATIVE_UNIT, PROVINCE]].dropna(subset=[ADMINISTRATIVE_UNIT])

    for col in [PROVINCE, ADMINISTRATIVE_UNIT]:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else None)

    # Use .notna() instead of != None for clarity and correctness
    unique_admin_units = df[ADMINISTRATIVE_UNIT].unique()
    valid_pairs = df[df[PROVINCE].notna()][ADMINISTRATIVE_UNIT].unique()

    for unit in set(unique_admin_units) - set(valid_pairs):
        logging.error(f"No valid province found for '{unit}'")

    return (
        df[df[ADMINISTRATIVE_UNIT].notna() & df[PROVINCE].notna()]
        .drop_duplicates()
        .apply(lambda row: {'name': row[ADMINISTRATIVE_UNIT], 'province': row[PROVINCE]}, axis=1)
        .tolist()
    )


def unique_strings(series: pd.Series) -> list[str]:
    return series.dropna().astype(str).str.strip().loc[lambda x: x != ''].unique().tolist()


def row_values(series: Union[pd.Series, list], sql_column: str) -> list[dict[str, str]]:
    values = series if isinstance(series, list) else unique_strings(series)
    return [{sql_column: value} for value in values]