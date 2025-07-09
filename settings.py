import logging
import os
from pathlib import Path
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import Engine, create_engine
from dotenv import load_dotenv

load_dotenv()

''' BASIC CONFIG'''

# General Settings
ALWAYS_CLEAN = True
SHOW_MISSING_ADDRESS = False

FUZZY_MATCH_ACCURACY = 90

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.getLogger("graphviz").setLevel(logging.WARNING)

''' PATHS '''

OUTPUTS = Path("data", "outputs")
INPUTS = Path("data", "inputs")

REF = Path("data", "ref")
REF_CSV = REF / "csv"
REF_JSON = REF / "json"

TRAINING_FILE = "apartment_for_rent_train.csv"
TESTING_FILE = "apartment_for_rent_test.csv"

ADDRESSES = REF_CSV / "addresses.csv"
TRANSLATIONS = REF_CSV / "translated.csv"
GEOCODED = REF_CSV / "geocoded.csv"

ARMENIAN_REGION = REF_JSON / "armenian_region.json"
EXCHANGE_RATES = REF_JSON / "exchange_rates.json"

''' KEYS '''

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")

''' REQUEST HEADERS '''

# https://learn.microsoft.com/en-us/rest/api/maps/search/get-geocoding?view=rest-maps-2025-01-01&tabs=HTTP#request-headers
AZURE_API_PARAMS = {
    'api-version': '1.0',
    'subscription-key': AZURE_API_KEY,
    'language': 'en-US',  
    'countrySet': 'AM,GE,AZ',
    'limit': 1,         
}

# https://github.com/sandstrom/country-bounding-boxes/blob/master/bounding-boxes.json
BBOXES = { 
    "Armenia": [43.58, 38.74, 46.51, 41.25],
    "Georgia": [39.96, 41.06, 46.64, 43.55],
    "Azerbaijan": [44.79, 38.27, 50.39, 41.86]
}

# https://yandex.com/maps-api/docs/geocoder-api/request.html
YANDEX_API_PARAMS = {
    'apikey': YANDEX_API_KEY,
    'format': 'json',
    'results': 1,
    'lang': 'en_US',
    'bbox': "39.96,38.27~50.39,43.86",
    'rspn': 1
}

''' DATABASE '''

DB_USERNAME = "adam"
DB_PASSWORD = "password"
DB_NAME = "summative"
DB_ADDRESS = "localhost"
DB_PORT = 5433 # Changed From Default 5432

engine: Engine = create_engine(f'postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_ADDRESS}:{DB_PORT}/{DB_NAME}')
session: Session = sessionmaker(bind=engine)()

SQL_PATH = OUTPUTS / "database.sql"