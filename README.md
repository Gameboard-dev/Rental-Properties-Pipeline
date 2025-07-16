
### Data Preprocessing

The Pandas library was used to load and process the CSV (comma-delimited) data. 

**Majority Dtype Casting:** To avoid hardcoded column mappings, data types were inferred. If the majority of a column's values could be converted to numeric, it was treated as numeric; otherwise, it was handled as a string. This improved the flexibility of the code, and reduced boilerplate code.

**Normalization**: This was applied using compiled regular expressions to ensure consistent formatting across text fields. This included replacing underscores, "none", and multiple spaces with a single space; normalizing Unicode and accented characters; removing punctuation; and converting strings to title case. Boolean columns such as 'Furniture' and 'Balcony', which contained various truthy or falsy strings, were explicitly encoded as binary booleans. A new column representing monthly rental price in USD was added. This involved two steps: converting daily rates to monthly rates using the number of days in the month, and then converting all prices to USD using historical exchange rates tied to the listing date and the currency.

**Data Validation:** Records missing critical fields—such as date, address, or price—were removed, and the reasons for exclusion were logged for transparency. Several sanity checks were also performed to identify and remove implausible or logically inconsistent entries. These included verifying that the apartment's floor did not exceed the total number of floors in the building, that the number of bathrooms did not exceed the number of rooms, and that the total floor area exceeded 10. Entries with a ceiling height of zero were also excluded as invalid. The floor area was assumed to be measured in square meters, as a median around 70 aligned with standard apartment sizes in that unit; interpreting it as square feet (~6.5 m²) would not be as realistic. Duplicate rows—entries with identical values across all columns—were also removed, under the assumption that such exact repetition is unlikely to occur naturally and likely indicates error in data entry.

**Outlier Removal:** Outlier removal was done in multiple stages using percentiles. Prices were grouped by Currency (AUD, USD) and Rental Duration ('Monthly', 'Daily') to assess them within their distribution. Floor area and price outliers were found using a 1% upper and lower percentile (or 98% IQR - Inter Quartile Range). An additional round of outlier filtering was performed on the normalized price. The choice of thresholds was informed by trial and error and remains subjective. Note that the percentiles used at this stage had a significant impact on the graphs produced at the analysis stage.

**Address Mapping:** Unique address strings were mapped into structured components including Country, Province, Administrative Zone (e.g., Municipality or District for Yerevan), Town, Street, and other fields such as Street Number, Lane or Block Number, and Building Code. This pcombined the use of Google Cloud Translate, geocoding API, compiled regular expressions, and hardcoded mappings to known regional area names. The hierarchial structure of the region allowed reverse lookups to be conducted on, say, a municipality belonging to a certain province. The goal of this transformation was to prepare the data for storage in a relational database that adheres to Third Normal Form (3NF).

- **First Normal Form (1NF):** Ensures that each field contains a single, atomic value—no sets, lists, or comma-separated entries. Storing multiple address components in one column violates 1NF.

- **Second Normal Form (2NF):** Requires that all non-key attributes are fully dependent on the entire primary key, which is relevant when using composite keys.

- **Third Normal Form (3NF):** Eliminates transitive dependencies by ensuring that all non-key attributes depend only on the primary key — not indirectly through another non-key field.
    
- **Amenities, Appliances, and Parking:** These columns required special handling due to inconsistent formatting. In the test set, values were "none", while in the training set, many rows contained comma-separated lists (e.g., "washer, dryer, microwave"). To facilitate database normalization,  analytics, and modelling, these lists were transformed using One-Hot Encoding. This involved normalizing their strings, splitting the lists into individual attributes, and encoding each as a binary column indicating presence (1) or absence (0) in a row. Each attribute then was prefixed with a group identifier (e.g., 1_ for amenities), supporting integration into a relational "many-to-one" schema structure. The "parking_space" entry was removed from the "amenities" column to avoid artificially inflating its correlation with the target variable (Price), since the same information was already captured in the separate "Parking" column. **Rank** columns were then fitted which essentially summed the number of 1s captured for each group on a given row or property.

<img width="666" height="592" alt="image" src="https://github.com/user-attachments/assets/2ed7b157-2693-4c31-a923-1f6a715bca61" />

Throughout the entire cleaning process, every exclusion was logged with a clear and specific reason. The excluded rows, with these reasons, were saved separately, supporting traceability, and facilitating potential recovery of removed data, which aligns with recommended practices for [data provenance and auditability](https://www.acceldata.io/blog/data-provenance).


### Address Parsing Pipeline

![image](https://github.com/Gameboard-dev/Summative_Rewrite/blob/main/imgur.gif)

1. Sends batched API requests to Google Cloud Translate
2. Runs dockerized Nominatim / LibPostal and Yandex / Azure Maps API calls
3. Runs manual RegEx parsing and fuzzy matching hierarchial Armenian place names with 90% match
4. Normalizes address components using the following labels:

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

The pipeline is primarily designed to parse Armenian addresses into normalized components. To work with other regions, the Yandex bounding box (bbox) and Azure countrySet should be reconfigured in settings.py to reflect the target region. The hardcoded fuzzy regional area mappings in `data/ref/json/armenian_region.json` will also need to be extended or replaced to accommodate the new region's Provinces, Administrative Units, and Settlements, in order of hierarchial levels. Finally, the regular expressions may also need to be adapted based on the new region's address structure.


### Data Analytics

The following charts were generated using Seaborn and Matplotlib and can be reproduced in `scripts/analytics/visual`. You are recommended to use Visual Studio Code. To preserve statistical validity and reduce noise, rows with empty group attributes were excluded. Filtering was then applied to remove subgroups—defined by a combination of Province and Administrative Area—with fewer than 100 entries. Though subjective, 100 chosen to strike a balance between inclusion and statistical reliability. Higher cutoffs excluded too many minority groups and skewed the analysis toward Yerevan, while the 100-row minimum helped to eliminate sparse or unrepresentative samples. 

The high exclusion count in Fig. 1B—relative to the total of 33,175 records—was mainly due to many addresses missing a clearly defined street. Without this, it was not possible to group listings at the street level to calculate the standard deviation of average price changes over the (many) streetwise time series.

| Reason for Exclusion                                                     | Fig. 1A | Fig. 1B |
|--------------------------------------------------------------------------|---------|---------|
| 1. Required attribute was NULL                                           | 164     | 4493    |
| 2. Inadequate time-series length (< 2 records) to compute statistics     | 15      | 75      |
| 3. Aggregate size was below the minimum sample size (100)                | 680     | 472     |

Note that, due to low data size, changing the outliers from 5% to 1% (or vice versa) changes the data distribution, but Kentron remains at the top (expensive), and Gyumri at the bottom (affordable).

<img width="1896" height="938" alt="newplot" src="https://github.com/user-attachments/assets/6c9f5fad-ba83-4aac-9bcb-eef832a5d8fc" />

<img width="1886" height="906" alt="image" src="https://github.com/user-attachments/assets/4cc9ed76-f08f-4863-9bd2-bdcdfc6b4aed" />

<img width="1733" height="890" alt="image" src="https://github.com/user-attachments/assets/ed4f3ed3-7ef4-4aa2-8fb5-3b5809093f9a" />

<img width="763" height="590" alt="image" src="https://github.com/user-attachments/assets/9005f2c4-dcff-450b-9eca-1f98673221c6" />

<img width="1457" height="869" alt="image" src="https://github.com/user-attachments/assets/91076a0f-cc64-449e-8b0e-c70ea722a138" />

---

### Data Modelling

To uncover underlying patterns in the data, Principal Component Analysis (or PCA) was applied, which transforms high-dimensional data into a smaller number of uncorrelated components which capture the most variance. In this case, the feature space was reduced to four principal components, preserving the majority of the original information while eliminating redundancy. Following this transformation, the reduced dataset was clustered using the **KMeans** clustering algorithm, which partitioned the data into three distinct groups based on shared characteristics in the PCA reduced space.

<img width="628" height="400" alt="image" src="https://github.com/user-attachments/assets/b6d63757-278d-4eea-9c0b-84da84241cff" />

HistGBRT is an efficient, scalable version of traditional gradient boosting. Like other gradient boosting models, it builds an ensemble of decision trees sequentially—each new tree correcting the prediction errors of the previous ones. However, it differs in that it discretizes continuous numerical features into histogram bins, significantly reducing training time while maintaining predictive performance, and making it more robust to outliers in the data.

<img width="626" height="411" alt="image" src="https://github.com/user-attachments/assets/1871a9ab-8965-4ecf-9783-887eb023252f" />

Model performance was assessed using standard regression metrics, including Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), R², and Mean Absolute Percentage Error (MAPE). The model achieved an R² of 48.5%, indicating that nearly half of the variance in rental prices was explained by the input features. The Mean Absolute Error was $261.11, suggesting that on average, predicted prices deviated from actual prices by about $261.

To interpret model behavior, SHAP (SHapley Additive exPlanations) values were calculated across all predictions. SHAP analysis revealed that location—particularly the Kentron and Arabkir districts—had the strongest influence on predicted prices, followed by construction type (e.g., Monolith buildings), and interior condition. This aligns with real-world expectations, where geographic desirability, build quality, and living condition significantly drive rental value.

<img width="733" height="380" alt="image" src="https://github.com/user-attachments/assets/1f1cdc0f-dcf4-4339-941b-fe58cdf98f6d" />

---

### SQL Compilation and ERP Visualization

The following diagram, rendered as an SVG using Graphviz, follows standard UML notation. It was generated from a database schema defined using SQLAlchemy. In addition to visualization, the code also compiles the corresponding SQL statements needed to populate a PostgreSQL database with this schema, using the connection URL specified in the settings.

<img width="1257" height="644" alt="image" src="https://github.com/user-attachments/assets/9d6ebff5-ddd1-4369-b445-ffb63a653478" />

## License

This project is licensed for educational purposes.  

