import json
import pandas as pd
from scripts.columns import *
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

