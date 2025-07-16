

import ast
import numpy as np
import pandas as pd
from pathlib import Path
from pandas import DataFrame, Series
from pandas.api.types import is_string_dtype, is_bool_dtype
from scripts.address.normalize import apply_usd_monthly_pricing, title_strip_remove_punctuation_whitespace, normalize_string
from scripts.csv_columns import *
from settings import *


def is_mostly_numeric(series: pd.Series, threshold=0.8):
    converted = pd.to_numeric(series, errors='coerce') 
    return converted.notna().mean() > threshold


def column_by_majority_dtype(df: pd.DataFrame, threshold: float = 0.8):
    """ 
    Splits columns into 'numeric' and 'string' categories
    """
    cols = [col for col in df.columns if col != DATE and not is_bool_dtype(df[col])]
    numeric = [col for col in cols if is_mostly_numeric(df[col], threshold)]
    string = [col for col in cols if col not in numeric]
    return numeric, string


def string_casts(series: Series) -> Series:
    return (
        series.apply(lambda x: x.strip() if isinstance(x, str) else x)
              .astype("string")
              .fillna("")
    )


def binary_encoding(series: pd.Series) -> pd.Series:
    contains_mask = series.str.fullmatch(r"\s*|(0|not available)", case=False, na=False)
    return (~contains_mask).astype(bool)


def numeric_casts(series: Series) -> Series:
    return pd.to_numeric(series, errors='coerce').fillna(0)


def remove_outliers(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> tuple[pd.Series, pd.Index]:
    '''Return in-range values and the indices of excluded outliers.'''
    if not pd.api.types.is_numeric_dtype(series):
        series = pd.to_numeric(series, errors='coerce')
    quantiles = series.quantile([lower, upper])
    mask = (series >= quantiles.iloc[0]) & (series <= quantiles.iloc[1])
    return series[mask], series[~mask].index


def remove_grouped_outliers(
    df: pd.DataFrame,
    column: str,
    group_columns: list[str],  # <-- now a list!
    lower: float = 0.10,
    upper: float = 0.80
) -> tuple[pd.DataFrame, set[int]]:
    '''Remove outliers from a DataFrame column grouped by multiple other columns '''
    kept_indices = []
    retained_indices = set()

    for _, group_df in df.groupby(group_columns):
        filtered_series, excluded_idx = remove_outliers(group_df[column], lower, upper)
        kept_indices.extend(filtered_series.index)
        retained_indices.update(excluded_idx)

    cleaned_df = df.loc[kept_indices].reset_index(drop=True)
    return cleaned_df, retained_indices


def clean_and_comma_separate(row_value: str, column: str) -> list[str]:
    if pd.isna(row_value):
        return []

    # Normalize strings
    values = [
        normalize_string(value)
        for value in row_value.split(',')
        if normalize_string(value).strip().lower() not in {'', 'nan'}
    ]

    if column.lower() == 'amenities':
        values = [val for val in values if val != 'Parking Space']

    return values


def explode_and_dummify(series: pd.Series, prefix: str, column: str) -> pd.DataFrame:
    '''

    Step 1: Clean and comma-separate each entry into lists:
    -----------------------------------------------------------------------------------------
    | Amenities            | Appliances                                 | Parking            |
    |----------------------|--------------------------------------------|--------------------|
    | ["air_conditioner"]  | ["fridge", "stove", "washing_machine"]     | ["outdoor_parking"]|

    Step 2: Flatten the lists so that each value gets its own row. 
    The index is then repeated for strings of the same row.
    --------------------------------------------------------
    | Index | Value              |
    |-------|--------------------|
    | 0     | air_conditioner    |
    | 0     | fridge             |
    | 0     | stove              |
    | 0     | washing_machine    |
    | 0     | outdoor_parking    |

    Step 3: Apply dummy encoding with the column prefix and group by the index:

    {}"Amenities": 1, "Appliances": 2, "Parking": 3}
    ----------------------------------------------------

    | 1_Air Conditioner | 2_Fridge | 2_Stove | 2_Washing Machine | 3_Outdoor Parking |
    |-------------------|----------|---------|--------------------|-------------------|
    | 1                 | 1        | 1       | 1                  | 1                 |

    '''
    exploded: pd.Series = series.apply(lambda row : clean_and_comma_separate(row, column)).explode()
    return (
        pd.get_dummies(exploded, prefix=prefix)
        .groupby(level=0)
        .sum()
    )


def fill_missing_ranks(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure rank features exist and default to 0 if missing."""
    for col in [AMENITIES_RANK, APPLIANCES_RANK, PARKING_RANK]:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = df[col].fillna(0)
    return df


def rank_exploded_columns(df: pd.DataFrame) -> pd.DataFrame:
    ''' 
    Applies ranking to normalized dummy-encoded delimited attributes by summing up the values:

    | Amenities_Rank    | Appliances_Rank | Parking_Rank |
    |-------------------|-----------------|--------------|
    | 1                 | 2               | 0            |

    Ranked attributes can then be used for modelling and analysis.
    
    '''
    for prefix, column in PREFIX_TO_RANK_COLUMN.items():
        cols = [col for col in df.columns if col.startswith(prefix)]
        if cols:
            df[column] = df[cols].sum(axis=1).fillna(0)
        else:
            df[column] = pd.Series(0.0, index=df.index)
    return df


def apply_type_casts(df: DataFrame) -> DataFrame:
    df[DATE] = pd.to_datetime(df[DATE], format='mixed', dayfirst=True).dt.normalize()
    df[[ELEVATOR, NEW_CONSTRUCTION]] = df[[ELEVATOR, NEW_CONSTRUCTION]].fillna(False).astype(bool)
    numeric_columns, string_columns = column_by_majority_dtype(df)
    df[string_columns] = df[string_columns].apply(string_casts)
    df[numeric_columns] = df[numeric_columns].apply(numeric_casts)
    df[PRICE] = df[PRICE].astype(float)
    #logging.debug(df.dtypes)
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


def replace_column_names(df: DataFrame, path: Path) -> DataFrame:
    ''' Maps less verbose column names to shorter, database-friendly ones '''
    if any(col in df.columns for col in RENAMED.keys()):
        df = df.rename(columns=RENAMED)
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
    training = replace_column_names(training, training_path)
    testing = replace_column_names(testing, testing_path)
    # Update with aligned columns
    testing = map_training_to_testing_columns(src=training, trg=testing, trg_path=testing_path)
    return training, testing


def log_drop_reason(df_orig: DataFrame, exclude_ids: pd.Series, reason_col: str, reason_string: str):
    mask = df_orig[EXCLUSION_ID].isin(exclude_ids)
    df_orig.loc[mask, reason_col] = (
        df_orig.loc[mask, reason_col].fillna("") + reason_string + "; "
    )


def fill_missing_categories(df: pd.DataFrame) -> pd.DataFrame:
    for col in [ADMINISTRATIVE_UNIT, CONSTRUCTION, RENOVATION, STREET]:
        df[col] = df[col].fillna("")
    return df


def sanitize_data(df: DataFrame, filename: str, addresses: DataFrame = DataFrame) -> DataFrame:

    '''
    If the database is meant to store raw, factual data (e.g. listings), then imputing values can be misleading or even unethical. 
    You're essentially fabricating information, which violates the principle of database integrity.
    Which is why missing values are dropped and recorded or filled in as FALSE or 0.
    '''

    if not ALWAYS_CLEAN and (OUTPUTS / filename).exists():
        df = pd.read_csv(OUTPUTS / filename, encoding="utf-8")
        df = apply_type_casts(df)
        df[ADDRESS_COLUMNS] = df[ADDRESS_COLUMNS].apply(string_casts) 
        df[[FURNISHED, BALCONY]] = df[[FURNISHED, BALCONY]].fillna(False).astype(bool)
        df[MONTHLY_USD_PRICE] = df[MONTHLY_USD_PRICE].astype(float)
        logging.info(f"Loaded '{filename}'")
        return df
    
    # Apply dtype casting to columns in the original data
    df = apply_type_casts(df)

    # Record drop reasons for traceability
    df[EXCLUSION_ID] = range(len(df))
    original_df = df.copy()
    original_df[DROP_REASON] = ""

    # Drop sensitive PII
    df.drop(columns={"Reg_id", "Gender", "Age"} & set(df.columns), inplace=True)

    # Normalize strings
    string_columns = {col for col in df.columns if is_string_dtype(df[col])}
    normalize_cols = list(string_columns - {CURRENCY, AMENITIES, PARKING, APPLIANCES})
    df[normalize_cols] = df[normalize_cols].apply(title_strip_remove_punctuation_whitespace)
    df[RENOVATION] = df[RENOVATION].replace('', 'No Renovation')

    # Apply binary encoding (TRUE/FALSE)
    df[[FURNISHED, BALCONY]] = df[[FURNISHED, BALCONY]].apply(binary_encoding)

    # ========== DROP WITH LOGGING ==========

    # Missing Dates
    missing_ids = df.loc[df[DATE].isna(), EXCLUSION_ID]
    log_drop_reason(original_df, missing_ids, DROP_REASON, "Date was Missing")
    df = df.dropna(subset=[DATE]).copy()
    df[DATE] = pd.to_datetime(df[DATE], format='mixed', dayfirst=True).dt.normalize()

    # Missing Addresses
    missing_ids = df.loc[df[ADDRESS] == "", EXCLUSION_ID]
    log_drop_reason(original_df, missing_ids, DROP_REASON, "Address was Missing")
    df = df.dropna(subset=[ADDRESS]).copy()

    # Missing Prices
    missing_ids = df.loc[df[PRICE].isna(), EXCLUSION_ID]
    log_drop_reason(original_df, missing_ids, DROP_REASON, "Price was Missing")
    df = df.dropna(subset=[PRICE]).copy()
    df[PRICE] = pd.to_numeric(df[PRICE], errors='coerce')

    # Sanity Checks
    log_drop_reason(original_df, df.loc[df[FLOOR] > df[FLOORS], EXCLUSION_ID], DROP_REASON, "The floor exceeds than the number of floors in the building.")
    log_drop_reason(original_df, df.loc[df[BATHROOMS] > df[ROOMS], EXCLUSION_ID], DROP_REASON, "There were more bathrooms than rooms.")
    log_drop_reason(original_df, df.loc[df[FLOOR_AREA] <= 10, EXCLUSION_ID], DROP_REASON, "The area in square metres is less than 10.")
    log_drop_reason(original_df, df.loc[df[CEILING_HEIGHT] == 0, EXCLUSION_ID], DROP_REASON, "The ceiling height was missing or 0.")

    df = df[
        (df[FLOOR] <= df[FLOORS]) &
        (df[BATHROOMS] <= df[ROOMS]) &
        (df[FLOOR_AREA] > 10) &
        (df[CEILING_HEIGHT] != 0)
    ].copy()

    # Outlier Removal
    percentile = 1
    lower_decimal = percentile / 100; 
    upper_decimal = 1 - lower_decimal

    # Remove price outliers in the same quoted Currency and Duration
    df, outlier_idx = remove_grouped_outliers( df, column=PRICE, group_columns=[CURRENCY, DURATION], lower=lower_decimal, upper=upper_decimal)
    log_drop_reason(original_df, original_df.loc[list(outlier_idx), EXCLUSION_ID], DROP_REASON, f"The price was outside a {percentile}% IQR (Inter-Quartile Range) for its currency duration")

    # Floor Area Outliers
    filtered, outlier_idx = remove_outliers(df[FLOOR_AREA], lower_decimal, upper_decimal)
    log_drop_reason(original_df, df.loc[list(outlier_idx), EXCLUSION_ID], DROP_REASON, f"The Floor Area was Outside a {percentile}% IQR (Inter-Quartile Range)")
    df = df.loc[filtered.index].reset_index(drop=True)

    # Drop Duplicates
    mask = df.duplicated(keep="first")
    log_drop_reason(original_df, df.loc[mask, EXCLUSION_ID], DROP_REASON, "Row was a duplicate")
    df = df.drop_duplicates(keep="first").copy()

    # Map a MONTHLY_USD_PRICE onto each row for modelling purposes
    df = apply_usd_monthly_pricing(df)
    original_df[MONTHLY_USD_PRICE] = df[MONTHLY_USD_PRICE] = df[MONTHLY_USD_PRICE].astype(float)
    filtered, outlier_idx = remove_outliers(df[MONTHLY_USD_PRICE], lower_decimal, upper_decimal)
    log_drop_reason(original_df, df.loc[list(outlier_idx), EXCLUSION_ID], DROP_REASON, f"The Monthly USD price was outside a 1% IQR (Inter-Quartile Range)")
    df = df.loc[filtered.index].reset_index(drop=True)

    # Save exclusions df and drop the exclusions column
    exclusions = original_df[~original_df[EXCLUSION_ID].isin(df[EXCLUSION_ID])]
    exclusions_file: Path = OUTPUTS / (filename + "_excluded.csv")
    exclusions.to_csv(exclusions_file, index=False, encoding="utf-8")
    df = df.drop(columns=[EXCLUSION_ID])
    logging.info(f"Saved {len(exclusions)} removed rows to '{exclusions_file}'")

    # Map unique address components by row index ID
    df = map_rows_to_address_components(df, addresses)
    df[ADDRESS_COLUMNS] = df[ADDRESS_COLUMNS].apply(string_casts) 

    # Flatten and binary-encode comma-delimited amenities, appliances, and parking, into prefixed columns
    dummies = [explode_and_dummify(df[column], prefix, column) for column, prefix in PREFIX_MAPPING.items()]
    df = pd.concat([df.drop(columns=PREFIX_MAPPING.keys())] + dummies, axis=1) 



    # ------ Modelling Features ----------
    df[PRICE_BAND] = pd.cut(df[MONTHLY_USD_PRICE], bins=[0, 800, 2000, np.inf], labels=["Cheap", "Affordable", "Expensive"])
    df = rank_exploded_columns(df)

    df.to_csv(Path(OUTPUTS, filename), index=False, encoding="utf-8-sig")
    logging.info(f"Processed '{filename}'")

    return df