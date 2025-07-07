from scripts.csv_columns import *


YEREVAN_DISTRICTS: set[str] = {"Ajapnyak", "Avan", "Davtashen", "Erebuni", "Kanaker-Zeytun", "Kentron", "Malatia-Sebastia", "Nor Nork", "Nork-Marash", "Nubarashen", "Shengavit", "Arabkir", "Qanaqer-Zeytun"}

NOMINATIM_MAPPING: dict[str, str] = { # https://nominatim.org/release-docs/latest/api/Output/#addressdetails
    "house_number": BUILDING,
    "road": STREET,
    "highway": STREET,
    "country": COUNTRY,
    "state": PROVINCE,
    "state_district": ADMINISTRATIVE_UNIT,
    "municipality": ADMINISTRATIVE_UNIT,
    "city": TOWN,
    "town": TOWN,
    "village": VILLAGE,
    "suburb": NEIGHBOURHOOD,
    "neighbourhood": NEIGHBOURHOOD,
    "quarter": NEIGHBOURHOOD,
    "allotments": NEIGHBOURHOOD,
    "subdivision": NEIGHBOURHOOD,
    "city_block": BLOCK
}

AZURE_MAPPING: dict[str, str] = { # https://learn.microsoft.com/en-us/rest/api/maps/search/get-geocoding?view=rest-maps-2025-01-01&tabs=HTTP#address
    "countryRegion": COUNTRY,
    "locality": TOWN,
    "neighborhood": NEIGHBOURHOOD,
    "streetName": STREET,
}

YANDEX_MAPPING: dict[str, str] = { # https://yandex.com/maps-api/docs/geocoder-api/response.html
    "country": COUNTRY,
    "province": PROVINCE,
    "locality": TOWN,
    "street": STREET,
    "house": BUILDING,
    "area": ADMINISTRATIVE_UNIT,
    "district": NEIGHBOURHOOD,
}

LIBPOSTAL_MAPPING: dict[str, str] = { # https://github.com/openvenues/libpostal?tab=readme-ov-file#parser-labels
    "house_number": BUILDING,
    "city": TOWN,
    "state_district": ADMINISTRATIVE_UNIT,
    "state": PROVINCE,
    "country": COUNTRY,
}