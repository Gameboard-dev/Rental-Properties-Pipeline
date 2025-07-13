import logging
import numpy as np
import pandas as pd
from pandas import DataFrame
from scripts.address import TESTING_INDEX_PREFIX, TRAINING_INDEX_PREFIX
from scripts.address.normalize import normalize_address_parts
from scripts.api.geocode import load_geocoded_components
from scripts.api.translate import load_translations
from scripts.process import explode_addresses_on_index, string_casts, merge_on_unique
from scripts.address.separate import separate_into_unique_components, separate_on_hardcoded_delimiters, separate_hardcoded_regional_labels
from settings import ADDRESSES, INPUTS, TESTING_FILE, TRAINING_FILE
from scripts.csv_columns import *


def save_index(df: DataFrame, fileindex: str, file: str) -> DataFrame:
    df[ADDRESS_INDEX] = [f"{fileindex}{i}" for i in range(len(df))]
    df.to_csv(INPUTS / file, index=False, encoding="utf-8-sig")
    logging.debug(f"'{file}' has been saved with an address-index mapping.")
    return df


def map_address_indices(training: DataFrame, testing: DataFrame) -> DataFrame:
    """
    Associates each unique address with a list of row-level address indices
    from both training and testing datasets.
    """
    training = save_index(training, TRAINING_INDEX_PREFIX, TRAINING_FILE)
    testing = save_index(testing, TESTING_INDEX_PREFIX, TESTING_FILE)

    combined = pd.concat([training, testing])

    # Normalize addresses for consistent grouping
    combined[ADDRESS] = combined[ADDRESS].str.strip().str.lower()

    # Group by address and collect all row-level indices
    address_indices = (
        combined
        .groupby(ADDRESS)[ADDRESS_INDEX]
        .apply(list)
        .to_frame()
        .reset_index()
    )

    return address_indices


def remap_address_row_indices(training: DataFrame, testing: DataFrame, unique_addresses: DataFrame) -> DataFrame:
    logging.info("Remapping address indices")

    # Drop existing ADDRESS_INDEX column if it exists
    for df in [unique_addresses, training, testing]:
        if ADDRESS_INDEX in df.columns:
            df.drop(columns=[ADDRESS_INDEX], inplace=True)

    address_indices_map: DataFrame = map_address_indices(training, testing)

    # Normalize address columns to ensure consistent merging
    address_indices_map[ADDRESS] = address_indices_map[ADDRESS].str.strip().str.lower()
    unique_addresses[ADDRESS] = unique_addresses[ADDRESS].str.strip().str.lower()

    # Merge with full DataFrame
    unique_addresses = unique_addresses.merge(address_indices_map, on=ADDRESS, how="left")

    total = len(unique_addresses)
    missing = unique_addresses[unique_addresses[ADDRESS_INDEX].isna()]
    mapped = total - len(missing)

    # Log results
    logging.info(f"{mapped} out of {total} unique addresses successfully mapped to indices.")

    if not missing.empty:
        logging.warning(f"{len(missing)} addresses could not be mapped: {missing}")

    unique_addresses.to_csv(ADDRESSES, index=False, encoding="utf-8-sig")
    logging.info("Saved and reindexed 'training' and 'testing' data on 'Address'")
    return unique_addresses


ALWAYS_REMAP = False

def load_address_mapping(training: DataFrame, testing: DataFrame) -> DataFrame:
    ''' 
    Loads the address mapping processed and retrieved with process_address_mapping 
    Note some manual corrections were made to 1-2 addresses incorrectly returned by Yandex Maps
    '''
    if ADDRESSES.exists():

        addresses: DataFrame = pd.read_csv(ADDRESSES, encoding="utf-8")

        if ADDRESS_INDEX not in training.columns or ADDRESS_INDEX not in testing.columns or ALWAYS_REMAP:
            logging.info(f"Remapping {len(addresses)} address indices")
            addresses = remap_address_row_indices(training, testing, addresses)

        addresses[ADDRESS_COLUMNS] = addresses[ADDRESS_COLUMNS].apply(string_casts)
        return explode_addresses_on_index(addresses, ADDRESS_INDEX)
    
    else: 
        return process_address_mapping(training, testing)

'''
The following setup is required in order for the address parsing pipeline to run

- The following API keys in an `.env` in the ROOT directory as per https://pypi.org/project/python-dotenv/

    # https://developer.tech.yandex.ru/services/3
    YANDEX_API_KEY=

    # https://azure.microsoft.com/en-us/products/azure-maps/
    AZURE_API_KEY=

    # https://cloud.google.com/translate/docs/reference/rest/
    GOOGLE_APPLICATION_CREDENTIALS=

- The following up and running on Ubuntu WSL Docker container environments as per the docs:

    - Nominatim # https://github.com/mediagis/nominatim-docker/tree/master/5.1
    - LibPostal FastAPI # https://github.com/alpha-affinity/libpostal-fastapi

'''


def process_address_mapping(training: DataFrame, testing: DataFrame) -> DataFrame:

    logging.debug("Parsing addresses...")

    unique_addresses: DataFrame = (merge_on_unique([training[ADDRESS], testing[ADDRESS]]).astype(str).to_frame(name=ADDRESS).reset_index(drop=True)) # Deduplicated
    unique_addresses: DataFrame = load_translations(unique_addresses) # Loads Google Cloud Translate responses.
    unique_addresses: DataFrame = load_geocoded_components(unique_addresses) # Obtains geocoded responses for native and english language addresses including coordinates from Nominatim / Yandex / Azure / LibPostal
    
    unique_addresses[BLOCK] = ""; unique_addresses[LANE] = ""
    
    logging.debug("Normalizing abbreviations / spaces / punctuation / ASCII")

    unique_addresses.update({
        col: unique_addresses[col].apply(normalize_address_parts)
        for col in [TRANSLATED, STREET, NEIGHBOURHOOD]
    })

    logging.debug("Separating streets and cities on hardcoded delimiters.")

    unique_addresses[[STREET, TOWN]] = unique_addresses.apply( # Uses "," and "›" separators for failed geocoding attempts.
        lambda x: separate_on_hardcoded_delimiters(x, [STREET, TOWN])
        , axis=1
    ) 

    logging.debug("Separating streets into unique components.")

    unique_addresses = separate_into_unique_components(unique_addresses) # [Lane / Block / Neighbourhood / Building] regex pattern extraction. Fixes LibPostal putting districts into streets.
    
    logging.debug("Parsing hardcoded regional label values")

    unique_addresses = separate_hardcoded_regional_labels(unique_addresses)

    logging.debug("Mapping row address indices in training and testing sets.")

    unique_addresses[ADDRESS_COLUMNS] = unique_addresses[ADDRESS_COLUMNS].apply(string_casts) # Uses Pandas "string" dtype

    address_indices_map: DataFrame = map_address_indices(training, testing) # Map row indices in datasets to lists of row indices in unique_addresses
    unique_addresses = unique_addresses.merge(address_indices_map, on=ADDRESS, how="left")

    unique_addresses.to_csv(ADDRESSES, index=False, encoding="utf-8-sig", na_rep="")
    logging.debug("All addresses have been parsed and saved.")

    #unique_addresses = explode_addresses_on_index(unique_addresses, ADDRESS_INDEX) # Creates a separate row for each index mapping.
    return unique_addresses


if __name__ == "__main__":
    # python -m scripts.address.load
    from scripts.load import load_raw_datasets
    process_address_mapping(*load_raw_datasets())

