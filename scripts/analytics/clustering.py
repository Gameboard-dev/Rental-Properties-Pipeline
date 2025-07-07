import joblib
import pandas as pd
import numpy as np
from hdbscan import HDBSCAN
from pathlib import Path
from sklearn.metrics import r2_score, root_mean_squared_error
from sentence_transformers import SentenceTransformer
from scripts.csv_columns import NEIGHBOURHOOD, STREET, TOWN
from settings import *

'''
This script performs fuzzy grouping of addresses using text embeddings and clustering.
It uses the SentenceTransformer library to convert addresses into vector embeddings,
and then applies DBSCAN clustering to group similar addresses together.
Finally, it maps each cluster to a human-readable representative address which is the most frequent address in the cluster.

python -m analytics.clustering
'''

# Columns
SIMPLE_ADDRESS = 'Simple'
PRICE_COLUMN = 'Price'
CHANGE_COLUMN = 'Price % Change'
DATE_COLUMN = 'Datetime'

# Embedding Model
EMBEDDING_FILE  = Path("embeddings.npy")
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
BATCH_SIZE      = 64

# Clustering Model
CLUSTER_FILE = Path("hdbscan.joblib")
CLUSTER_MODEL  = HDBSCAN(min_cluster_size=10, metric="euclidean")
CLUSTER_COLUMN = "Cluster"


def generate_embeddings(texts: pd.Series) -> np.ndarray:
    """Load cached embeddings or compute & save as an NxD float32 array."""
    texts = texts.astype(str)
    if EMBEDDING_FILE.exists():
        print(f"Loaded {EMBEDDING_FILE}")
        return np.load(EMBEDDING_FILE)
    embeddings = np.vstack([
        EMBEDDING_MODEL.encode(chunk)
        for chunk in np.array_split(texts.to_numpy(), max(1, len(texts)//BATCH_SIZE))
    ]).astype(np.float32)
    np.save(EMBEDDING_FILE, embeddings)
    return embeddings


def generate_clusters(emb: np.ndarray) -> HDBSCAN:
    if CLUSTER_FILE.exists():
        print(f"Loaded {CLUSTER_FILE}")
        return joblib.load(CLUSTER_FILE)
    clusters: HDBSCAN = CLUSTER_MODEL.fit(emb)
    joblib.dump(clusters, CLUSTER_FILE)
    return clusters


def calculate_price_change(df: pd.DataFrame) -> pd.DataFrame:
    def price_change(group):
        new, old = group[PRICE_COLUMN].iloc[-1], group[PRICE_COLUMN].iloc[0]
        return 100 * (new - old) / old
    return (
        df
        .sort_values([CLUSTER_COLUMN, DATE_COLUMN])
        .groupby([CLUSTER_COLUMN, SIMPLE_ADDRESS])
        .apply(price_change)
        .reset_index(name=CHANGE_COLUMN)
    )


def order_matching_clusters(df: pd.DataFrame, clusters: set):
    df = df[df[SIMPLE_ADDRESS].fillna("").str.strip() != ""]
    df = df[df[CLUSTER_COLUMN].isin(clusters)]
    df = df.sort_values(CLUSTER_COLUMN).reset_index(drop=True)
    return df


def run_cluster_prediction_model(training: pd.DataFrame, testing: pd.DataFrame, addresses: pd.DataFrame):

    addresses[SIMPLE_ADDRESS] = (
        addresses[STREET]
          .fillna(addresses[NEIGHBOURHOOD])
          .str.cat(addresses[TOWN], sep=", ")
          .dropna()
    )

    addresses[SIMPLE_ADDRESS] = addresses[TOWN]

    embeddings: np.ndarray = generate_embeddings(addresses[SIMPLE_ADDRESS])

    clusters: HDBSCAN = generate_clusters(embeddings)
    addresses[CLUSTER_COLUMN] = clusters.labels_

    # Remove empty simple addresses or invalid (-1) clusters:
    mask = (addresses[CLUSTER_COLUMN] >= 0) & (addresses[SIMPLE_ADDRESS].str.strip() != "")
    addresses = addresses[mask]

    # Assign clusters to the testing and training datasets
    # ???

    common_clusters = set(training[CLUSTER_COLUMN]) & set(testing[CLUSTER_COLUMN])

    training, testing = [
        order_matching_clusters(df, common_clusters) for df in [training, testing]
    ]

    training = calculate_price_change(training)
    testing = calculate_price_change(testing)

    training_cluster_means = training.groupby(CLUSTER_COLUMN)[CHANGE_COLUMN].mean()

    y_true = testing[CHANGE_COLUMN]
    y_pred = testing[CLUSTER_COLUMN].map(training_cluster_means)

    rmse = root_mean_squared_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)
    print(f"RMSE: {rmse:.2f}, R²: {r2:.3f}")

    cluster_summary = (
        pd.concat([training, testing], axis=1)
        .reset_index()
    )

    cluster_summary.to_csv("clusters.csv", index=False, encoding="utf-8-sig")


if __name__ == '__main__':
    run_cluster_prediction_model()