import asyncio, aiohttp
import re
from collections import OrderedDict, defaultdict
from typing import Any, Optional, Tuple
import pandas as pd
from tqdm.asyncio import tqdm_asyncio
from scripts.address.normalize import normalize_address_parts
from scripts.api.parse import parse_azure_components, parse_libpostal_components, parse_nominatim_components, parse_yandex_components
from scripts.api.translate import is_non_english_string
from scripts.csv_columns import *
from settings import *

YANDEX_API_URL = "https://geocode-maps.yandex.ru/v1/"
NOMINATIM_API_URL = "http://localhost:8080/search"
AZURE_API_URL = "https://atlas.microsoft.com/search/address/json"
LIBPOSTAL_API_URL = "http://localhost:8001/parse"

STATUS_COLUMN = "Status"

MAX_RETRIES = 4
RETRY_BACKOFF = 5  # seconds

"""
'scripts.api.geocode'

Normalizes Armenian address records in a pandas DataFrame using a
multi-provider strategy. All results are returned in English and parsed into
normalized columns.

Parameters
----------
df : pandas.DataFrame
    DataFrame must include the following columns:
      - address: original address with Armenian or Russian characters
      - translation: address in English

Workflow
--------
For each row, attempts to geocode in this order until a match is found:
  1. Local Nominatim (OpenStreetMap) instance running on http://localhost:8080  
  2. Yandex API (restricted to a bounding box covering Armenia, Georgia, Azerbaijan)  
  3. Azure Maps API (restricted to the same countries)

With each provider:
  - Try the native address
  - Fall back to the English address

Fallback:
  - LibPostal with delimiter-based splitting and fuzzy matching  

Concurrency & Reliability
-------------------------
  - Uses asyncio + aiohttp for asynchronous API requests  
  - Implements retry logic, error handling, and logging  

Returns
-------
Normalized addresses with the following:

    - latitude              - village
    - longitude             - neighbourhood
    - country               - street_name
    - province              - lane
    - administrative_unit   - block
    - town                  - building_code
    - street_number

"""

async def query_nominatim(address: str, session: aiohttp.ClientSession) -> dict:
    # See Docker setup instructions ; docker start nominatim
    # http://localhost:8080/search.php?q=<address>&format=json&addressdetails=1&accept-language=en
    params = {
        "q": address,
        "format": "json",
        "addressdetails": 1,
        "accept-language": "en",
        "limit": 1
    }
    try:
        async with session.get(NOMINATIM_API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    components = parse_nominatim_components(data)
                    components['api'] = 'Nominatim'
                    logging.info(f"Nominatim geocoded address '{address}' successfully.")
                    return components
            else:
                logging.error(f"Nominatim failed for address '{address}' with status {response.status}")
    except Exception as e:
        logging.error(f"Nominatim exception for '{address}': {e}")
    return {}


async def query_yandex(address: str, session: aiohttp.ClientSession) -> dict:
    params = YANDEX_API_PARAMS.copy()
    params['geocode'] = address

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(YANDEX_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data:
                        logging.error(f"Yandex returned empty response for '{address}'")
                        return {}
                    components, formatted = parse_yandex_components(data)
                    if components and formatted:
                        components['api'] = 'Yandex'
                        logging.info(f"Yandex geocoded '{address}' as '{formatted}'")
                        return components
                    else:
                        logging.warning(f"Yandex failed to parse components for '{address}'")
                        return {}
                elif response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    delay = int(retry_after) if retry_after else RETRY_BACKOFF * attempt
                    logging.warning(f"Yandex rate-limited on '{address}' (429). Retrying after {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logging.error(f"Yandex error for '{address}' — status {response.status}")
                    return {}
        except Exception as e:
            logging.warning(f"Yandex retry {attempt}/{MAX_RETRIES} failed for '{address}': {e}")
            await asyncio.sleep(RETRY_BACKOFF * attempt)
    return {}




async def query_azure(address: str, session: aiohttp.ClientSession) -> dict:
    # https://atlas.microsoft.com/search/address/json?api-version=1.0&subscription-key=API_KEY&query=ADDRESS
    params = AZURE_API_PARAMS.copy()
    params['query'] = address
    try:
        async with session.get(AZURE_API_URL, params=params) as response:
            if response.status == 200:
                raw_response: dict = await response.json()
                results = raw_response.get("results", [])

                if not results:
                    logging.error("No results returned from Azure Maps")
                    return {}
                
                try:
                    components, formatted = parse_azure_components(results)
                    if components and formatted:
                        components['api'] = 'Azure'
                        logging.info(f"Azure geocoded address '{address}' as '{formatted}' successfully.")
                        return components
                except (IndexError, KeyError) as e:
                    logging.error(f"Encountered an error when parsing Azure response for '{address}': {e}")
                    return {}
            else:
                logging.error(f"Azure failed for address '{address}' with status {response.status}")
                return {}
    except Exception as e:
        logging.error(f"Azure encountered an exception when geocoding address '{address}': {e}")
        return {}


def address_candidates(row: pd.Series) -> list[str]:
    """ Extracts address candidates using hardcoded columns. """
    return [address for s in (row.get(ADDRESS, ''), row.get(TRANSLATED, '')) if (address := str(s).strip())]



GEOCODERS = OrderedDict([
    ("Yandex", query_yandex),
    ("Nominatim", query_nominatim),
    ("Azure", query_azure)
])

GEOCODERS_REVERSED = OrderedDict(reversed(list(GEOCODERS.items())))

async def try_geocoders_on_row(address: str, session: aiohttp.ClientSession) -> dict:

    geocoders: dict = GEOCODERS if is_non_english_string(address) else GEOCODERS_REVERSED
        
    results: dict[str, Any] = {}

    for name, query in geocoders.items():
        if response := await query(address, session):
            for key, value in response.items():
                if key not in results:
                    results[key] = value

    return dict(results)


async def geocode_row(row: pd.Series, session: aiohttp.ClientSession) -> dict:
    """
    Attempts to geocode a single row using multiple APIs.
    - Skips geocoding if the row has been geocoded (row["Status"] == "OK").
    - If no services succeed, sets the "Status" to "FAILED".
    """

    if row.get(STATUS_COLUMN, 'Pending') == 'OK':
        return row.to_dict()

    [native_address, translated] = address_candidates(row)
            
    if not (native_address or translated):
        # Fail if both are missing
        row[STATUS_COLUMN] = 'FAILED'
        return row.to_dict()

    # Then query the geocoding services to obtain the full address components including latitude and longitude.
    for candidate in [native_address, translated]:

        if not candidate: 
            continue

        if components := await try_geocoders_on_row(candidate, session):

            row[STATUS_COLUMN] = 'OK'
            
            for key, value in components.items(): 
                row[key] = value

            await asyncio.sleep(2)
            return row.to_dict()

    row[STATUS_COLUMN] = 'FAILED'
    return row.to_dict()


async def geocode_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    async with aiohttp.ClientSession() as session:
        tasks = [geocode_row(row, session) for idx, row in df.iterrows()]
        dicts = await tqdm_asyncio.gather(*tasks)
        return pd.DataFrame(dicts)


def load_geocoded_components(df: pd.DataFrame) -> pd.DataFrame:
    """ Loads existing geocoded or geocodes the DataFrame with Yandex, Nominatim, and Azure Maps."""

    if TRANSLATED and ADDRESS not in df.columns:
        raise ValueError(f"Columns '{TRANSLATED}' and '{ADDRESS}' are required.")

    if GEOCODED.exists() and not os.getenv("ALWAYS_GEOCODE") == "True":
        logging.info(f"Loaded existing components from '{GEOCODED}'")
        return pd.read_csv(GEOCODED, encoding="utf-8-sig")
    
    else:
        logging.info(f"Loading geocoded components ...")
        geocoded: pd.DataFrame = asyncio.run(geocode_dataframe(df))
        geocoded.to_csv(GEOCODED, encoding="utf-8")
        return geocoded


if __name__ == "__main__":
    # python -m scripts.api.geocode
    '''
    The following setup is required in order for the address parsing pipeline to run

    - The following API keys in an `.env` in the ROOT directory as per https://pypi.org/project/python-dotenv/

        # https://developer.tech.yandex.ru/services/3
        YANDEX_API_KEY=

        # https://azure.microsoft.com/en-us/products/azure-maps/
        AZURE_API_KEY=

        # https://cloud.google.com/translate/docs/reference/rest/
        GOOGLE_KEY_FILE=

    - The following up and running on Ubuntu WSL Docker container environments as per the docs:

        - Nominatim # https://github.com/mediagis/nominatim-docker/tree/master/5.1
        - LibPostal FastAPI # https://github.com/alpha-affinity/libpostal-fastapi

    '''
    os.environ["ALWAYS_GEOCODE"] = "True"
    if TRANSLATIONS.exists():
        df = pd.read_csv(TRANSLATIONS, encoding="utf-8-sig")
        geocoded: pd.DataFrame = load_geocoded_components(df)
        geocoded.to_csv(GEOCODED, index=False, encoding="utf-8-sig")
    else:
        raise FileNotFoundError(f"There is no '{TRANSLATIONS}' file.")


