import logging
import os
from pathlib import Path
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import Engine, create_engine
from dotenv import load_dotenv

load_dotenv()

# General Settings
ALWAYS_CLEAN = True
SHOW_MISSING_ADDRESS = False

FUZZY_MATCH_ACCURACY = 90

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

OUTPUTS = Path("data", "outputs")
INPUTS = Path("data", "inputs")

REF = Path("data", "ref")
REF_CSV = REF / "csv"
REF_JSON = REF / "json"

TRAINING = "training.csv"
TESTING = "testing.csv"

ADDRESSES = REF_CSV / "addresses.csv"
TRANSLATIONS = REF_CSV / "translated.csv"
GEOCODED = REF_CSV / "geocoded.csv"

ARMENIAN_REGION = REF_JSON / "armenian_region.json"
EXCHANGE_RATES = REF_JSON / "exchange_rates.json"

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

DB_USERNAME = "adam"
DB_PASSWORD = "password"
DB_NAME = "summative"
DB_ADDRESS = "localhost"
DB_PORT = 5433 # Changed From Default 5432

engine: Engine = create_engine(f'postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_ADDRESS}:{DB_PORT}/{DB_NAME}')
session: Session = sessionmaker(bind=engine)()

