

import ast
from typing import List, Optional
import pandas as pd
from pathlib import Path
from pandas import DataFrame, Series
from scripts.columns import *
from settings import *


FEATURE_PREFIXES = {
    AMENITIES: 1,
    APPLIANCES: 2,
    PARKING: 3
}

def string_casts(series: Series) -> Series:
    return series.astype("string").fillna("")


def binary_encoding(series: Series) -> Series:
    mask: Series[bool] = series.str.contains(r"^0$|not available", regex=True, case=False).fillna(False)
    return (~mask).astype(int)


def numeric_casts(series: Series) -> Series:
    return pd.to_numeric(series, errors='coerce')


def string_normalization(series: Series) -> Series:
    return (series
            .str.replace("none", "", case=False)
            .str.replace(r'\s+|_', ' ', regex=True)
            .str.strip()
            .str.title())


def remove_outliers(series: Series, lower: float = 0.01, upper: float = 0.99) -> Series:
    ''' Drop upper and lower percentiles in a Numeric Series '''
    if not pd.api.types.is_numeric_dtype(series):
        pd.to_numeric(series, errors='coerce')

    return series[(series >= series.quantile(lower)) 
                & (series <= series.quantile(upper))]


def explode_and_dummify(series: pd.Series, prefix: str) -> pd.DataFrame:
    return (
        pd.get_dummies(series.explode(), prefix=prefix)
        .groupby(level=0)
        .sum()
    )


def run_type_casts(df: DataFrame) -> DataFrame:
    df[STRING_COLUMNS] = df[STRING_COLUMNS].apply(string_casts)
    df[NUMERIC_COLUMNS].apply(numeric_casts)
    return df


def listify(val):
    if isinstance(val, str):
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):
            return [val]
    return val


def explode_addresses_on_index(df: DataFrame, index_column: str) -> DataFrame:
    """Explodes a DataFrame on an index column containing stringified or actual lists."""
    if index_column not in df.columns:
        raise KeyError(f"{index_column} needs to be in 'addresses.csv' to explode on index.")
    df[index_column] = df[index_column].apply(listify)
    return df.explode(index_column).reset_index(drop=True)


def unique_values(series: List[Series]) -> Series:
    """Retrieves unique, non-null values from multiple Series into a single Series"""
    return pd.concat(series, ignore_index=True).dropna().drop_duplicates()


def map_rows_to_address_components(df: pd.DataFrame, addresses: pd.DataFrame) -> pd.DataFrame:
    df.drop(columns=[ADDRESS], inplace=True, errors='ignore') # DUPLICATE
    df = pd.merge(
        df,
        addresses,
        on=ADDRESS_INDEX,
        how='left'
    )
    if SHOW_MISSING_ADDRESS: return df
    else:
        df.drop(columns=['OK'], inplace=True, errors='ignore')
        return df


def sanitize(filename: str, addresses: DataFrame) -> DataFrame:

    raw = Path(INPUTS, filename)
    clean = Path(OUTPUTS, filename)

    if not ALWAYS_CLEAN and clean.exists():
        df = pd.read_csv(clean, encoding="utf-8")
        df = run_type_casts(df)
        logging.info(f"Loaded '{filename}'")

    elif raw.exists():

        df = pd.read_csv(raw, encoding="utf-8")

        df = run_type_casts(df)

        # Drop superflous columns
        drop = {"Reg_id", "Gender", "Age"} & set(df.columns)
        df.drop(columns=drop, inplace=True)
        
        df[STRING_COLUMNS] = df[STRING_COLUMNS].apply(string_normalization)

        # Binary encoding
        binary = [FURNISHED, BALCONY]
        df[binary] = df[binary].apply(binary_encoding)

        # Outlier removal
        df[PRICE] = remove_outliers(df[PRICE], lower=0.10, upper=0.80)

        # Sanity checks
        df = df[(df[FLOOR] <= df[FLOORS]) & (df[BATHROOMS] <= df[ROOMS])]

        dummies = [explode_and_dummify(df[column], prefix) 
                for column, prefix in FEATURE_PREFIXES.items()]

        df = (pd.concat([df] + dummies, axis=1)
            .drop(columns=FEATURE_PREFIXES.keys()))
        
        df = map_rows_to_address_components(df, addresses)

        df.to_csv(Path(OUTPUTS, filename), index=False, encoding="utf-8-sig")

        logging.info(f"Processed '{filename}'")

    return df