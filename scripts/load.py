import logging
import pandas as pd
from typing import Tuple
from pandas import DataFrame
from scripts.address.load import load_address_mapping
from scripts.csv_columns import AMENITIES
from scripts.process import run_prerequisite_column_check, sanitize_data
from settings import INPUTS, TRAINING_FILE, TESTING_FILE


def load_raw_datasets() -> Tuple[DataFrame, DataFrame]:
    """Loads training and testing datasets from CSV"""
    return (pd.read_csv(INPUTS / file, encoding="utf-8") for file in [TRAINING_FILE, TESTING_FILE])


def load() -> tuple[DataFrame, DataFrame]:
    ''' Loads '''
    training, testing = load_raw_datasets()
    training, testing = run_prerequisite_column_check(training, testing) # Testing lacks proper column names. Order matches training.
    addresses = load_address_mapping(training, testing)
    training = sanitize_data(training, TRAINING_FILE, addresses)
    testing = sanitize_data(testing, TESTING_FILE, addresses)
    return training, testing, addresses


if __name__ == '__main__':
    # python -m scripts.load
    training, testing, addresses = load()
        

        