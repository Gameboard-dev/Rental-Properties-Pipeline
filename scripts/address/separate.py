import logging
import json, re
from typing import Optional
import pandas as pd
from pandas import DataFrame
from scripts.address.lookup import fuzzy_match, retrieve_armenian_regional_structure, reverse_lookup
from scripts.address.normalize import NEIGHBOURHOOD_SUFFIX, ORDINAL_RGX, ORDINAL_SUFFIX, WHITESPACE_RGX
from scripts.columns import *

BLOCK_RGX = re.compile(
    rf"""
    \b
    (?:[A-Za-z]+(?:[-\s][A-Za-z]+)*\s+)?  # Optional prefix (e.g., Davidashen, Ani-)
    \d*(?:{ORDINAL_SUFFIX})?\s*          # Optional number with ordinal suffix
    (Block|Blok)\b                        # 'Block' or 'Blok'
    """,
    flags=re.VERBOSE | re.IGNORECASE
)

LANE_RGX = re.compile(
    rf'\b\d+{ORDINAL_SUFFIX}\s+(?:Lane|Alley|Line|Deadlock)\b',
    flags=re.IGNORECASE
)

BUILDING_RGX = re.compile(
    rf"""
    \b
    (?!\d{{1,3}}-?{ORDINAL_SUFFIX}\b)   # Negative lookahead for ordinals
    \d{{1,3}}                           # 1-3 digits
    (?:[-/]\d+)?                        # Optional hyphen or slash and digits
    [a-zA-Z]?                           # Optional character (e.g., 'A' in 123A)
    \b
    """,
    flags=re.VERBOSE | re.IGNORECASE
)

NEIGHBOURHOOD_SUBDISTRICTS_RGX = re.compile(
    rf"""
    (                                   # Begin capturing group
        [A-Za-z0-9\-\s]+?               # Named prefix (?)
        \b{NEIGHBOURHOOD_SUFFIX}\b      # Matches suffix like 'quarter'
        (?:\s+[A-Za-z0-9\-]+)?          # Optional trailing letters (e.g., 'North', 'West')
    )                                   
    """,
    flags=re.IGNORECASE | re.VERBOSE
)

STREET_COMPONENTS_RGX = {
    BLOCK: BLOCK_RGX,
    LANE: LANE_RGX,
    BUILDING: BUILDING_RGX,
    NEIGHBOURHOOD: NEIGHBOURHOOD_SUBDISTRICTS_RGX,
    STREET_NUMBER: ORDINAL_RGX
}

PATTERN_TO_STRING = {
    BLOCK_RGX: "Block Pattern", 
    LANE_RGX: "Lane Pattern", 
    BUILDING_RGX: "Building Code Pattern", 
    NEIGHBOURHOOD: "Neighbourhood and Subdistricts Pattern", 
    STREET_NUMBER: "Street Number Pattern"
}

def return_final_match(string: str, pattern: re.Pattern) -> Optional[re.Match]:
    """ Optionally returns the last pattern match if found in a string """
    matches = list(pattern.finditer(string))
    return matches[-1] if matches else None


def separate_regex_match(value: str, pattern: re.Pattern, reverse: bool = False, trim: bool = True) -> pd.Series:
    """
    Extracts a regex match from a string.
    Returns:
        pd.Series: A Series with two elements:
            [0] The modified string (with match removed if trim=True),
            [1] The matched substring (or "" if no match is found).
    """
    match: Optional[re.Match] = return_final_match(value, pattern) if reverse else pattern.search(value)
    matched = match.group(0) if match else ""

    if trim and matched:
        value: str = value.replace(matched, "", 1)

    return pd.Series([value.strip(), matched.strip()])

NUMBERED_STREETS = {
    "August": "August 23 Street",
    "Commissars": "26 Commissars Street"
}

def assign_regex_match(row: pd.Series, pattern: re.Pattern, source_column: str, assign_column: str, reverse: bool = False, keep_original: bool = False) -> pd.Series:
    """
    Helper to extract a regex match and assign it to the appropriate column.
    Preserves the existing assign-column value. Always trims from the source-column value.
    """
    try:

        if pd.isna(row[source_column]):
            return pd.Series({source_column: row[source_column], assign_column: row[assign_column]})
        
        value = str(row.get(source_column))
        trimmed, matched = separate_regex_match(value, pattern, reverse)

        if existing_assign := str(row.get(assign_column, "")).strip():
            matched = existing_assign

        for name, expanded in NUMBERED_STREETS.items():
            if assign_column == BUILDING and name in trimmed:
                trimmed = expanded
                matched = ""

        if keep_original:
            trimmed = value

        return pd.Series({source_column: trimmed, assign_column: matched})
    
    except Exception as e:
        logging.warning(f"Failed to separate on pattern {PATTERN_TO_STRING[pattern]} for value {value} \n {e}")


def fix_generic_streets(row: pd.Series) -> pd.Series:
    '''
    Fixes cases where the street field is generic (like just 'street') by enriching it with a town or zone name 
    Removes streets which equal exactly ANY regional value like 'Abovyan'
    Assumes row values use Pandas "string" dtypes which allow NA values.
    '''

    if pd.isna(row[STREET]):
        return row
    
    stripped: str = WHITESPACE_RGX.sub(' ', str(row[STREET]))

    if not stripped: 
        return row

    for col in [TOWN, VILLAGE, ADMINISTRATIVE_UNIT, PROVINCE, COUNTRY]:

        if pd.isna(row[col]): 
            continue

        column_value: str = str(row[col]).strip()

        if not column_value:
            continue

        if stripped == column_value:
            #logging.debug(f"{value} == {row[col]}")
            row[STREET] = pd.NA
            return row

        if stripped == "Street":
            row[STREET] = f"{column_value} {stripped}"

        else:
            row[STREET] = stripped

    return row


def separate_into_unique_components(df: DataFrame) -> DataFrame:
    """Separates BLOCK, LANE, STREET_NUMBER, NEIGHBOURHOOD and BUILDING components from STREET and/or NEIGHBOURHOOD into their own columns using compiled regex patterns."""
    
    for column, pattern in STREET_COMPONENTS_RGX.items():
        reverse_lookup: bool = column == BUILDING
        df[[STREET, column]] = df.apply(
            lambda row: assign_regex_match(row, pattern, STREET, column, reverse_lookup),
            axis=1
        )

    df[[NEIGHBOURHOOD, BLOCK]] = df.apply(lambda row: assign_regex_match(row, BLOCK_RGX, NEIGHBOURHOOD, BLOCK), axis=1) # Fixed geocoded neighbourhoods being blocks
    
    # Operate on the TRANSLATED column value with the ordinalized Neighbourhood
    df[[TRANSLATED, BUILDING]] = df.apply(lambda row: assign_regex_match(row, BUILDING_RGX, TRANSLATED, BUILDING, reverse=True, keep_original=True), axis=1) # Fixed missing building codes in geocoded outputs

    df = df.apply(fix_generic_streets, axis=1)

    return df


def separate_on_hardcoded_delimiters(row: pd.Series, index_columns: list[str]) -> pd.Series:
    """
    Uses "," and "›" delimiters in splitting a TRANSLATED address into 'STREET' and 'TOWN' or reverse if "›"
    Keeps existing values.
    """
    # If both columns already have values, skip splitting
    if all(str(row.get(col, "")).strip() for col in index_columns):
        return pd.Series({col: row.get(col, "") for col in index_columns})

    if address := str(row.get(TRANSLATED, "")):

        parts = [""] * len(index_columns)

        for delim in [",", "›"]:
            if delim in address:
                split_parts = address.split(delim, maxsplit=len(index_columns) - 1)
                split_parts = [p.strip() if len(p.strip()) >= 3 else "" for p in split_parts]
                if delim == "›":
                    split_parts = split_parts[::-1]
                parts = (split_parts + [""] * len(index_columns))[:len(index_columns)]
                break

        # Preserve any existing non-empty values
        for i, col in enumerate(index_columns):
            if str(row.get(col, "")).strip():
                parts[i] = row[col]

        return pd.Series(dict(zip(index_columns, parts)))


def separate_hardcoded_regional_labels(df: pd.DataFrame) -> pd.DataFrame:
    """ Separates hardcoded Armenian regional label values (Province, Municipality, District, Settlement) into hardcoded columns """

    (provinces, administrative_units_mapping, locality_mapping) = retrieve_armenian_regional_structure()

    df[PROVINCE] = df[TRANSLATED].apply(lambda x: fuzzy_match(x, choices=provinces))

    df[ADMINISTRATIVE_UNIT] = df.apply(
        lambda row: fuzzy_match(row[TRANSLATED], choices=administrative_units_mapping.keys()), axis=1
    )

    df[TOWN] = df.apply(
        lambda row: fuzzy_match(row[TRANSLATED], choices=locality_mapping.keys()) if row[PROVINCE] != "Yerevan" else "", axis=1
    )

    df[PROVINCE] = df.apply(
        lambda row: reverse_lookup(row[ADMINISTRATIVE_UNIT], administrative_units_mapping) if not str(row[PROVINCE]).strip() else row[PROVINCE], axis=1
    )
        
    df[ADMINISTRATIVE_UNIT] = df.apply(
        lambda row: reverse_lookup(row[TOWN], locality_mapping) if not str(row[ADMINISTRATIVE_UNIT]).strip() else row[ADMINISTRATIVE_UNIT], axis=1
    )



    return df