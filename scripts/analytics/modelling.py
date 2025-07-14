import logging
import re
from typing import Union
import pandas as pd
import numpy as np
import scipy
import shap
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from scripts.analytics.evaluation import evaluate_predictions
from scripts.analytics.visual import visualize_explained_variance, visualize_pca_clusters, visualize_prediction_errors
from scripts.csv_columns import *

# ---------------------- Constants ----------------------

CLUSTERS: int = 3
PCA_N: int = 3
SHAPLEY_ADDITIVE_EXPLANATIONS = True

NUMERIC_COLUMNS: list[str] = [DURATION, APPLIANCES_RANK, AMENITIES_RANK]
CATEGORICAL_COLUMNS: list[str] = [ADMINISTRATIVE_UNIT, CONSTRUCTION, RENOVATION, STREET]

SHAPLEY_LABEL_REGEX = re.compile(
    r'^(cat_|num_)?(?:' + '|'.join([re.escape(col) for col in NUMERIC_COLUMNS + CATEGORICAL_COLUMNS]) + r')_(?P<value>.+)$'
)

def clean_shapley_label(label: str) -> str:
    match = SHAPLEY_LABEL_REGEX.match(label)
    return match.group("value") if match else label


# ---------------------- Feature Engineering ----------------------

def build_preprocessor() -> ColumnTransformer:
    """
    Builds a preprocessing pipeline:
    - One-hot encodes categorical variables
    - Standardizes numeric variables
    """
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
        ("num", StandardScaler(), NUMERIC_COLUMNS)
    ])

# ---------------------- Clustering ----------------------

def cluster_with_principle_components(df: pd.DataFrame, preprocessor: ColumnTransformer, n_clusters: int = CLUSTERS) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Performs PCA for dimensionality reduction and applies KMeans clustering.
    Adds cluster labels to the DataFrame
    """
    X = df[CATEGORICAL_COLUMNS + NUMERIC_COLUMNS]
    X = preprocessor.transform(X)

    visualize_explained_variance(X)

    pca = PCA(n_components=PCA_N)
    X = pca.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(X)

    visualize_pca_clusters(X, labels)

    df["Cluster"] = labels

    logging.info(f"Assigned {n_clusters} clusters")
    return df, X, labels


# ---------------------- Modeling ----------------------

def train_random_regressor(df: pd.DataFrame, description: str) -> tuple[ColumnTransformer, RandomForestRegressor]:
    """
    Fits a HistGradientBoostingRegressor to the given DataFrame.
    Returns the fitted preprocessor and the model.
    """
    if df.empty:
        raise ValueError(f"No data found for training '{description}' model")

    X = df[CATEGORICAL_COLUMNS + NUMERIC_COLUMNS]
    y = df[MONTHLY_USD_PRICE]

    preprocessor: ColumnTransformer = build_preprocessor()
    X_processed: Union[np.ndarray, scipy.sparse.spmatrix] = preprocessor.fit_transform(X)

    if hasattr(X_processed, "toarray"):
        X_processed = X_processed.toarray()

    model = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.1)
    model.fit(X_processed, y)

    logging.info(f"{description} model trained on {len(df)} rows")
    return preprocessor, model


def train_cluster_models(train_df: pd.DataFrame) -> dict[int, tuple[ColumnTransformer, RandomForestRegressor]]:
    cluster_models = {}
    for cluster_id in train_df["Cluster"].unique():
        cluster_df = train_df[train_df["Cluster"] == cluster_id]
        if not cluster_df.empty:
            preprocessor, model = train_random_regressor(cluster_df, f"Cluster {cluster_id}")
            cluster_models[cluster_id] = (preprocessor, model)
    return cluster_models


# ---------------------- Prediction ----------------------

def prediction(df: pd.DataFrame, preprocessor: ColumnTransformer, model: RandomForestRegressor, model_name: str) -> pd.Series:
    """
    Runs prediction on the DataFrame using the trained model.
    """
    if df.empty:
        logging.warning(f"Unable to make a prediction with the {model_name} model. Testing DF has no matching rows.")
        return pd.Series([], dtype=float)
    X = df[CATEGORICAL_COLUMNS + NUMERIC_COLUMNS]
    return model.predict(preprocessor.transform(X))


def make_predictions_by_cluster(test_df: pd.DataFrame, cluster_models: dict[int, tuple[ColumnTransformer, RandomForestRegressor]]) -> pd.DataFrame:

    explained: bool = False # Run once because PermutationExplainer takes a while to run

    for cluster_id, (preprocessor, model) in cluster_models.items():

        cluster_rows = test_df[test_df["Cluster"] == cluster_id]

        if cluster_rows.empty:
            continue

        # Preprocess columns with preprocessor
        X_processed = preprocessor.transform(cluster_rows[CATEGORICAL_COLUMNS + NUMERIC_COLUMNS])

        if hasattr(X_processed, "toarray"): # Casts to a dense numpty array for HistGradientBoostingRegressor
            X_processed = X_processed.toarray()

        # Run a prediction
        preds = model.predict(X_processed)
        test_df.loc[test_df["Cluster"] == cluster_id, "Predicted"] = preds.round(2)

        if not explained and SHAPLEY_ADDITIVE_EXPLANATIONS:

            names = [clean_shapley_label(name) for name in preprocessor.get_feature_names_out()]

            # SHAP Explanations (XAI)
            explainer = shap.Explainer(model.predict, X_processed, feature_names=names)
            shap_values = explainer(X_processed)

            shap.plots.bar(shap_values)                 # Global additive effects
            shap.plots.waterfall(shap_values[0])        # Row 0 explanation

            shap_df = pd.DataFrame(shap_values.values, columns=names)
            shap_df["Cluster"] = cluster_id
            shap_df["RowIndex"] = cluster_rows.index.values 

            logging.info("Shapley Additive Explanations were saved")
            shap_df.to_csv(f"shap_cluster_{cluster_id}.csv", index=False)

            explained = True

    return test_df


def assign_clusters_and_sample(df: pd.DataFrame, test_size: float = 0.2, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, ColumnTransformer]:
    """Clusters the full dataset, then does train/test splits"""

    transformer = build_preprocessor()
    transformer.fit(df[CATEGORICAL_COLUMNS + NUMERIC_COLUMNS])

    clustered_df, _, labels = cluster_with_principle_components(df, transformer, CLUSTERS)
    clustered_df["Cluster"] = labels

    train_df = clustered_df.sample(frac=1 - test_size, random_state=seed)
    test_df = clustered_df.drop(train_df.index)

    logging.info(f"Train/Test Split: {len(train_df)} train rows, {len(test_df)} test rows")
    return train_df, test_df, transformer


# ---------------------- Execution ----------------------

if __name__ == "__main__":

    # python -m scripts.analytics.modelling

    logging.basicConfig(level=logging.INFO)

    from scripts.load import load

    # Load and prepare full dataset
    df1, df2, _ = load()
    df = pd.concat([df1, df2], ignore_index=True)

    df[DURATION] = df[DURATION] == "Monthly"

    # Cluster the data, add cluster labels, and assign splitting with labelled rows
    train_df, test_df, transformer = assign_clusters_and_sample(df)

    # Train cluster-specific models on training set
    logging.info("Training cluster models...")
    cluster_models = train_cluster_models(train_df)

    # Run predictions on matching clusters in test set using the gradient boosting model:
    logging.info("Predicting on test set...")
    prediction_df = make_predictions_by_cluster(test_df, cluster_models)

    # Evaluate results
    evaluate_predictions(prediction_df)

    visualize_prediction_errors(prediction_df)


