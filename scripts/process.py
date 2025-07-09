

import ast
import pandas as pd
from pathlib import Path
from pandas import DataFrame, Series
from scripts.address.normalize import normalize_column, normalize_string
from scripts.csv_columns import *
from settings import *


def string_casts(series: Series) -> Series:
    return (
        series.apply(lambda x: x.strip() if isinstance(x, str) else x)
              .replace("", pd.NA)
              .astype("string")
    )


def binary_encoding(series: pd.Series) -> pd.Series:
    series = series.astype(str)
    contains_mask = series.str.contains(r"^0$|not available", regex=True, case=False, na=False)
    return (~contains_mask).astype(int)


def numeric_casts(series: Series) -> Series:
    return pd.to_numeric(series, errors='coerce').fillna(0)


def remove_outliers(series: Series, lower: float = 0.01, upper: float = 0.99) -> Series:
    ''' Drop upper and lower percentiles in a Numeric Series '''
    if not pd.api.types.is_numeric_dtype(series):
        pd.to_numeric(series, errors='coerce')

    return series[(series >= series.quantile(lower)) 
                & (series <= series.quantile(upper))]


def clean_and_comma_separate(x) -> list[str]:
    if pd.isna(x):
        return []
    return [
        normalized for value in str(x).split(',')
        if (normalized := normalize_string(value)).strip().lower() not in {'', 'nan'}
    ]


def explode_and_dummify(series: pd.Series, prefix: str) -> pd.DataFrame:
    '''
    Turn comma delimited column entries into a Series of lists of strings.
    Explode (flatten) the lists so each string becomes its own row remaining linked to a (duplicated) row index
    Create one-hot encoded columns for each unique string with a column prefix
    Re-group (aggregate) the encoded value by the (duplicated) row index (level=0)
    '''
    exploded: pd.Series = series.apply(clean_and_comma_separate).explode()
    return (
        pd.get_dummies(exploded, prefix=prefix)
        .groupby(level=0)
        .sum()
    )


def run_type_casts(df: DataFrame) -> DataFrame:
    df[STRING_COLUMNS] = df[STRING_COLUMNS].apply(string_casts)
    df[NUMERIC_COLUMNS].apply(numeric_casts)
    df[DATE] = pd.to_datetime(df[DATE], format="%d/%m/%Y").dt.date
    df[[FURNISHED, BALCONY, ELEVATOR]] = df[[FURNISHED, BALCONY, ELEVATOR]].fillna(False).astype(bool)
    return df


def apply_list(val):
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
    df[index_column] = df[index_column].apply(apply_list)
    return df.explode(index_column).reset_index(drop=True)


def merge_on_unique(series: list[Series]) -> Series:
    """Retrieves unique, non-null values from multiple Series into a single Series"""
    return pd.concat(series, ignore_index=True).dropna().drop_duplicates()


def map_rows_to_address_components(df: pd.DataFrame, addresses: pd.DataFrame) -> pd.DataFrame:
    # Drop ADDRESS column if exists to avoid duplication
    df.drop(columns=[ADDRESS], inplace=True, errors='ignore')
    # Merge address components into the DataFrame
    df = pd.merge(df, addresses, on=ADDRESS_INDEX, how='left')
    # Optionally drop 'OK' if not showing missing address
    if not SHOW_MISSING_ADDRESS:
        df.drop(columns=['OK'], inplace=True, errors='ignore')
    return df


def rewrite_columns(df: DataFrame, path: Path) -> DataFrame:
    '''
    Maps less verbose column names to shorter, database-friendly ones.
    '''
    if any(col in df.columns for col in RENAMED_COLUMNS.keys()):
        df = df.rename(columns=RENAMED_COLUMNS)
        logging.info("Column names rewritten for consistency.")
        df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def map_training_to_testing_columns(src: DataFrame, trg: DataFrame, trg_path: Path) -> DataFrame:
    ''' Replace testing column names with those from training '''
    if src.shape[1] == trg.shape[1] and not src.columns.equals(trg.columns):
        logging.info("Overwrote testing data columns with training data columns.")
        trg.columns = src.columns
        trg.to_csv(trg_path, index=False, encoding="utf-8-sig")
    return trg


def run_prerequisite_column_check(training: DataFrame, testing: DataFrame):
    training_path = INPUTS / TRAINING_FILE
    testing_path = INPUTS / TESTING_FILE
    training = rewrite_columns(training, training_path)
    testing = rewrite_columns(testing, testing_path)
    # Update with aligned columns
    testing = map_training_to_testing_columns(src=training, trg=testing, trg_path=testing_path)
    return training, testing


def sanitize_data(df: DataFrame, filename: str, addresses: DataFrame = DataFrame) -> DataFrame:

    if not ALWAYS_CLEAN and (OUTPUTS / filename).exists():
        df = pd.read_csv(OUTPUTS / filename, encoding="utf-8")
        df = run_type_casts(df)
        # These are done separately being added at the end of processing
        df[ADDRESS_COLUMNS] = df[ADDRESS_COLUMNS].apply(string_casts) 
        logging.info(f"Loaded '{filename}'")
        return df

    df = run_type_casts(df)
    
    # Drop unnecessary personal or sensitive information
    drop = {"Reg_id", "Gender", "Age"} & set(df.columns)
    df.drop(columns=drop, inplace=True)

    columns_to_normalize = [
        col for col in STRING_COLUMNS
        if col in df.columns
        if col not in ADDRESS_COLUMNS
        and col != CURRENCY
    ]

    df[columns_to_normalize] = df[columns_to_normalize].apply(normalize_column)

    # Binary encoding
    binary = [FURNISHED, BALCONY]
    df[binary] = df[binary].apply(binary_encoding)

    # Date encoding
    df[DATE] = pd.to_datetime(df[DATE], format="%d/%m/%Y").dt.date

    # Drop missing prices and outliers
    df[PRICE] = pd.to_numeric(df[PRICE], errors='coerce')
    df = df.dropna(subset=[PRICE])
    df = df.loc[remove_outliers(df[PRICE], 0.10, 0.80).index].reset_index(drop=True)

    df[FLOOR_AREA] = df[FLOOR_AREA].fillna(0).astype(int)

    # Sanity checks
    df = df[(df[FLOOR] <= df[FLOORS]) & (df[BATHROOMS] <= df[ROOMS]) & (10 < df[FLOOR_AREA])]

    df = map_rows_to_address_components(df, addresses)

    for column, prefix in PREFIX_MAPPING.items():
        cleaned = df[column].apply(clean_and_comma_separate)
        #logging.debug(f"{column} → unique values: {set(val for sublist in cleaned for val in sublist)}")

    # Note - will fail if both dataframes contain all None
    dummies = [explode_and_dummify(df[column], prefix) 
            for column, prefix in PREFIX_MAPPING.items()]
    
    df = pd.concat([df.drop(columns=PREFIX_MAPPING.keys())] + dummies, axis=1)

    df[ADDRESS_COLUMNS] = df[ADDRESS_COLUMNS].apply(string_casts) 

    df.to_csv(Path(OUTPUTS, filename), index=False, encoding="utf-8-sig")

    logging.info(f"Processed '{filename}'")

    return df