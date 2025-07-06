import pandas as pd
from typing import Tuple
from pandas import DataFrame
from scripts.address.load import load_address_mapping, process_address_mapping
from scripts.process import sanitize_raw_datafiles
from settings import INPUTS, TRAINING, TESTING


def load_raw_datasets() -> Tuple[DataFrame, DataFrame]:
    """Loads training and testing datasets from CSV"""
    return (pd.read_csv(INPUTS / name, encoding="utf-8") for name in [TRAINING, TESTING])

def load() -> tuple[DataFrame, DataFrame]:
    addresses: DataFrame = load_address_mapping()
    if addresses.empty: addresses = process_address_mapping(*load_raw_datasets())
    return sanitize_raw_datafiles(TRAINING, addresses), sanitize_raw_datafiles(TESTING, addresses)



        

        