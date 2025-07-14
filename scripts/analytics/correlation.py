import logging
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.io as pio
import seaborn as sns
from scipy.stats import spearmanr, norm, pointbiserialr
from scripts.csv_columns import *

pio.renderers.default = 'browser' 

def correlation_ci(r, n, alpha=0.05):
    """Calculate 95% confidence intervals using Fisher Z-transform"""
    if n <= 3 or abs(r) == 1.0:
        return np.nan, np.nan
    z = 0.5 * np.log((1 + r) / (1 - r))
    se = 1 / np.sqrt(n - 3)
    z_crit = norm.ppf(1 - alpha / 2)
    ci_low = np.tanh(z - z_crit * se)
    ci_high = np.tanh(z + z_crit * se)
    return ci_low, ci_high

def significance_label(p):
    if p < 0.001:
        return "P < 0.001"
    elif p < 0.01:
        return "P < 0.01"
    elif p < 0.05:
        return "P < 0.05"
    else:
        return ""

def effect_strength_label(r):
    if abs(r) >= 0.6:
        return "Strong"
    elif abs(r) >= 0.3:
        return "Moderate"
    elif abs(r) > 0:
        return "Weak"
    else:
        return ""

def draw_correlation_matrix(column_series: pd.DataFrame, binary_columns: list = []):
    columns = column_series.columns
    corr_matrix = pd.DataFrame(np.eye(len(columns)), index=columns, columns=columns)
    pval_matrix = pd.DataFrame(np.zeros_like(corr_matrix), index=columns, columns=columns)

    for row in columns:
        for col in columns:
            if row == col:
                continue

            x = column_series[row]
            y = column_series[col]
            n_obs = min(x.dropna().shape[0], y.dropna().shape[0])
            try:
                is_binary = row in binary_columns or col in binary_columns
                if is_binary:
                    corr, pval = pointbiserialr(x, y)
                    method = "point biserial"
                else:
                    corr, pval = spearmanr(x, y)
                    method = "spearman"

                corr_matrix.loc[row, col] = corr
                pval_matrix.loc[row, col] = pval
                ci_low, ci_high = correlation_ci(corr, n_obs)

                logging.info(f"{method.title()} Correlation between {row} and {col}: "
                             f"r = {corr:.4f}, p = {pval:.2e}, CI = [{ci_low:.2f}, {ci_high:.2f}]")

            except Exception as e:
                logging.warning(f"Error comparing {row} and {col}: {e}")
                corr_matrix.loc[row, col] = np.nan
                pval_matrix.loc[row, col] = np.nan

    labels = pd.DataFrame("", index=columns, columns=columns)
    for row in columns:
        for col in columns:
            r = corr_matrix.loc[row, col]
            p = pval_matrix.loc[row, col]
            if row == col:
                labels.loc[row, col] = "1.00"
            elif pd.isna(r):
                labels.loc[row, col] = "NaN"
            else:
                r_str = f"{r:.2f}"
                p_str = significance_label(p)
                e_str = effect_strength_label(r)
                labels.loc[row, col] = f"{r_str}\n{p_str}\n{e_str}"

    # Plot heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=labels, cmap='coolwarm', fmt="", center=0,
                linewidths=0.5, linecolor='gray')
    plt.title("Correlation Matrix with Significance & Effect Strength")
    plt.tight_layout()
    plt.show()






