import asyncio, aiohttp
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

''' 
Takes a DataFrame with native and English translations of addresses.
Geocodes Armenian addresses using multiple providers:
- Nominatim (OpenStreetMap) assuming a local instance running on 8080
- Yandex Geocoder API with a bounding box restricted to Armenia, Georgia, and Azerbaijan
- Azure Maps Geocoder API with a country set restricted to Armenia, Georgia, and Azerbaijan
- Tries each geocoding service in turn until one succeeds.
- Attempts the native address, and then falls back to the English translation.
- If all else fails, uses the LibPostal statistical parser as a fallback.
- Uses asynchronous requests to speed up the geocoding process.
- Handles errors and logs them.
- Returns results in English and parses them into standardized columns.
'''

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
    """
    Queries the Yandex Geocoder API for a given address
    Restricts the call to addresses within a bounding box (BBOX)
    """
    params = YANDEX_API_PARAMS.copy()
    params['geocode'] = address
    try:
        async with session.get(YANDEX_API_URL, params=params) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    if not data:
                        logging.error(f"Yandex returned an empty response for {address}")
                        return {}
                    components: dict = parse_yandex_components(data)
                    components['api'] = 'Yandex'
                    logging.info(f"Yandex geocoded address '{address}' successfully.")
                    return components
                except (IndexError, KeyError, ValueError) as e:
                    logging.error(f"Yandex failed to parse address '{address}': {e}")
                    return {}
            else:
                logging.error(f"Yandex failed for address '{address}' with status {response.status}")
                return {}

    except Exception as e:
        logging.error(f"Yandex encountered an exception when geocoding address '{address}': {e}")
        return {}


async def query_azure(address: str, session: aiohttp.ClientSession) -> dict:
    # Note: Azure Maps API was not needed for the addresses, but included for future extensibility.
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
                    components = parse_azure_components(results)
                    components['api'] = 'Azure'
                    logging.info(f"Azure geocoded address '{address}' successfully.")
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


async def query_libpostal(address: str, session: aiohttp.ClientSession) -> dict:
    ''' LibPostal is used as a fallback parsing method in case no services finds a known address '''
    try:
        async with session.get(LIBPOSTAL_API_URL, params={"address": address}) as response:
            if response.status == 200:
                data = await response.json()
                if not data:
                    return {}
                components = {label: value for value, label in data}
                components = parse_libpostal_components(components)
                components["api"] = "Libpostal"
                return components
            else:
                logging.error(f"Libpostal failed for address '{address}' with status {response.status}")
    except Exception as e:
        logging.error(f"Libpostal exception for '{address}': {e}")
    return {}


def address_candidates(row: pd.Series) -> list[str]:
    """ Extracts address candidates using hardcoded columns. """
    return [address for s in (row.get(ADDRESS, ''), row.get(TRANSLATED, '')) if (address := str(s).strip())]

async def try_geocoders(address: str, session: aiohttp.ClientSession, english_characters: bool) -> dict:
    for query in [
        query_nominatim,
        query_azure if english_characters else None,
        query_yandex,
    ]:
        if query:
            response: dict = await query(address, session)
            if response:
                return response
    return {}

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

        english_characters: bool = not is_non_english_string(candidate)

        if components := await try_geocoders(candidate, session, english_characters):

            row[STATUS_COLUMN] = 'OK'
            
            for key, value in components.items(): 
                row[key] = value

            await asyncio.sleep(0.2)
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


