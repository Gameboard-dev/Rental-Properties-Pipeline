# Address Parsing Pipeline

![image](https://github.com/Gameboard-dev/Summative_Rewrite/blob/main/imgur.gif)

1. Sends batched API requests to Google Cloud Translate
2. Runs dockerized Nominatim / LibPostal and Yandex / Azure Maps API calls
3. Runs manual RegEx parsing and fuzzy matching hierarchial Armenian place names with 90% match
4. Normalizes address components
   
|                    |                    |                    |
|--------------------|--------------------|--------------------|
| a. Country         | e. Lane            | i. Village         |
| b. Building Code   | f. Block           | j. Administrative Unit |
| c. Street          | g. Neighbourhood   | k. Province        |
| d. Street Number   | h. Town            |                    |

---

![Image](https://github.com/Gameboard-dev/Summative_Rewrite/blob/main/docs/images/Excel.png)

> **Note:** Viewing CSV files in MS Excel requires **'getData' -> UTF-8** to avoid corrupting non-ASCII characters or turning building codes into dates.

---

## Setup Instructions

The following setup is required in order for the address parsing pipeline to run

1. [Configure Google Translate](docs/google_cloud.md)

2. [Configure Nominatim](docs/nominatim.md)

3. [Configure LibPostal](docs/libpostal.md)

4. [Configure Yandex Maps API](docs/yandex_maps.md)

5. [Configure Azure Maps API](docs/azure_maps.md)

6. [Configure PostgreSQL](docs/postgresql.md)


The following API keys should be in an `.env` file in the ROOT directory as per ['dotenv'](https://pypi.org/project/python-dotenv/) instructions.

    YANDEX_API_KEY=<api_key>
    >https://developer.tech.yandex.ru/services/3

    AZURE_API_KEY=<api_key>
    >https://azure.microsoft.com/en-us/products/azure-maps/

    GOOGLE_APPLICATION_CREDENTIALS=<path/to/keyfile.json>
    >https://cloud.google.com/translate/docs/reference/rest/


The pipeline is mainly configured to parse Armenian addresses into normalized components.


## License
Licensed for educational purposes.
