
import logging
from scripts.api import *
from scripts.csv_columns import *


def parse_nominatim_components(data: list[dict]) -> dict:
    """
    Parses structured address components from a Nominatim geocoding API response.
    https://nominatim.org/release-docs/latest/api/Output/
    """
    parsed = {}

    try:
        response: dict = data[0]  # (Nominatim returns a series)
        address_fields: dict = response.get("address", {})

        parsed[LATITUDE] = float(response.get("lat", .0))
        parsed[LONGITUDE] = float(response.get("lon", .0))

        suburb: str = address_fields.get("suburb", "")
        if suburb in YEREVAN_DISTRICTS:
            parsed[ADMINISTRATIVE_UNIT] = suburb
            address_fields["suburb"] = None

        locality: str = address_fields.get("locality", "")
        if locality:
            if "village" in str(locality).lower():
                parsed[VILLAGE] = locality
                address_fields["locality"] = None

        # https://nominatim.org/release-docs/latest/api/Output/#addressdetails
        for nominatim_label, csv_column in NOMINATIM_MAPPING.items():
            if value := address_fields.get(nominatim_label):
                parsed[csv_column] = value

    except (IndexError, KeyError, TypeError) as e:
        logging.warning(f"Error parsing Nominatim components: {e}")

    return parsed


def parse_azure_components(results) -> dict:
    """
    Parses structured address components from Azure Maps Geocoding API response.
    https://learn.microsoft.com/en-us/rest/api/maps/search/get-geocoding?view=rest-maps-2025-01-01&tabs=HTTP
    https://atlas.microsoft.com/search/address/json?api-version=1.0&subscription-key=AZURE_API_KEY&query=2nd+microdistrict,+Abovyan
    """

    parsed = {}

    try:

        result = results[0]
        address = result.get("address", {})

        if address:
            parsed[PROVINCE] = address.get("countrySubdivision")
            parsed[ADMINISTRATIVE_UNIT] = address.get("countrySecondarySubdivision") or address.get("municipality")
            parsed[NEIGHBOURHOOD] = address.get("neighbourhood")
            parsed[TOWN] = address.get("locality")
            parsed[STREET] = f"{address.get('streetName', '')} {address.get('streetNumber', '')}".strip()
            parsed[COUNTRY] = address.get("country")

            position = result.get("position", {})
            parsed[LATITUDE] = position.get("lat")
            parsed[LONGITUDE] = position.get("lon")

            for azure_label, csv_column in AZURE_MAPPING.items():
                if value := address.get(azure_label):
                    parsed[csv_column] = value

    except (KeyError, IndexError, TypeError) as e:
        logging.warning(f"Error parsing Azure components {results}: {e}")

    return parsed


def parse_yandex_components(data: dict) -> dict:
    """
    Parses structured address components from a Yandex Geocoder API.
    Extracts coordinates and address parts based on the 'kind' field.
    https://yandex.com/maps-api/docs/geocoder-api/response.html
    """
    parsed = {}

    try:
        geo_objects = data["response"]["GeoObjectCollection"]["featureMember"]
        geo = geo_objects[0]["GeoObject"]
        meta = geo["metaDataProperty"]["GeocoderMetaData"]
        components = meta["Address"]["Components"]

        # Map address components by 'kind'
        components_map = {comp["kind"]: comp["name"] for comp in components}

        # Yandex returns "lon lat" as a string
        coords: str = geo["Point"]["pos"]
        longitude, latitude = map(float, coords.split())
        parsed[LONGITUDE] = longitude
        parsed[LATITUDE] = latitude

        locality: str = components_map.get("locality", "")
        if locality:
            if "village" in str(locality).lower():
                parsed[VILLAGE] = locality
                components_map["locality"] = None

        for label, csv_column in YANDEX_MAPPING.items():
            if value := components_map.get(label):
                parsed[csv_column] = value

    except (KeyError, IndexError, TypeError) as e:
        logging.warning(f"Error parsing Yandex components: {e}")

    return parsed


def parse_libpostal_components(data) -> dict:
    """ Parses libpostal address components into a normalized schema """
    parsed = {}
    for label, csv_column in LIBPOSTAL_MAPPING.items():
        if value := data.get(label):
            parsed.setdefault(csv_column, value.strip())
    return parsed