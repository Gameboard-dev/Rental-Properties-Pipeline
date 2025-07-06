## Assumptions and Address Ambiguities

To ensure our cluster embedding model yields meaningful results, it’s essential to recognize the following caveats in address data:
- Identical street names existing in multiple towns
- Armenian and Russian addresses use different character sets
- Some addresses lack street details entirely, referencing only a town or neighborhood
- Building numbers, street/block numbers often carry excessive granularity and are thus excluded from clustering

---

## Address Transformation Pipeline

To standardize and prepare address data for clustering, we implemented the following transformations:

1. **Local Codification with Nominatim**  
   - Used a local instance of Nominatim with Armenian data to translate ~4,700 addresses from native Armenian to their parsed English form.

2. **Parsing Multilingual Addresses**  
   - Remaining addresses were parsed using:
     - Asynchronous calls to Google Translate
     - Compiled regular expressions for building and block codes
     - Fuzzy matching with curated sets of provinces and municipalities

3. **Imputation and Validation**  
   - Ordered addresses alphabetically by 'Street' and then by 'City'
   - Cross-referenced mistranslated/rare addresses with Yandex or Bing Maps
   - Overwrote parsed components with a validated value correcting spelling mistakes
   - Filled in missing coordinates for the same 'Street' in the same 'City'
   - Inferred missing 'City' by geocoordinate range

6. **Simplified Address Synthesis**  
   - Constructed a normalized address structure for use with an embedding clustering model:
     - Excluded building, block, and street number as overly granular or superflous
     - Retained only one of either street or neighborhood and always included the town

7. **Vectorization & Clustering**  
   - The simplified addresses were converted into vector embeddings
   - Vectors for the same address with minor typos or spelling errors matched to the same clusters.
   - The clustering model obtained cluster assignments (1, 2, 3 ...) which were joined to the 'addresses.csv' data via decoded embedding values.

8. **Modelling Address Clusters on Price Changes**
   - 'addresses.csv' was mapped to rows in the training and testing sets using an 'Index' unique to each row. This was obtained to avoid issues with minor corrections in 'addresses.csv' causing mismatches and breaking address lookup.
   - The average rental price change was calculated for every cluster using the beginning and end dates in the training data. The outcomes were used as predictions for the same clusters in the testing data.
   - The significance of these assignments as a proxy for similar address values, for predicting the change in rental prices, was found based on the discrepancy between the predicted and actual rental price increase (or decrease), and thus the predictive power of the address's general area.
   






