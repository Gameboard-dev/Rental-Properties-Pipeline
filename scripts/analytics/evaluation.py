


import logging
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, mean_absolute_error, mean_squared_error, r2_score
from scripts.csv_columns import MONTHLY_USD_PRICE


def evaluate_predictions(df: pd.DataFrame) -> None:

    """Logs performance metrics for predictions."""
    df["Actual"] = df[MONTHLY_USD_PRICE]
    df["Error"] = (df["Actual"] - df["Predicted"]).round(2)

    missing_clusters = df[df["Predicted"].isna()]["Cluster"].value_counts()

    if missing_clusters.empty:
        logging.info("No missing predictions — all clusters covered.")
    else:
        logging.info(f"Missing predictions from clusters:\n{missing_clusters}")

    df = df.dropna(subset=["Predicted", "Actual"])
    if df.empty:
        logging.warning("No valid rows after dropping NaNs — skipping evaluation.")
        return

    # Metrics
    mse = mean_squared_error(df["Actual"], df["Predicted"])
    rmse = np.sqrt(mse)
    r2 = r2_score(df["Actual"], df["Predicted"])
    mae = mean_absolute_error(df["Actual"], df["Predicted"])
    mape = (np.abs(df["Actual"] - df["Predicted"]) / df["Actual"]).mean() * 100

    logging.info(f"MAPE: {mape:.2f}%")
    logging.info(f"MAE: ${mae:.2f}")
    logging.info(f"RMSE: ${rmse:.2f}")
    logging.info(f"R² Score: {r2:.3f}")

