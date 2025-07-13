
import logging
import seaborn as sns
import operator
import numpy as np
import pandas as pd
import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go
from functools import reduce
from sklearn.decomposition import PCA
from scripts.analytics import compute_distance
from scripts.analytics.correlation import draw_correlation_matrix
from scripts.csv_columns import *
from typing import Optional
from matplotlib import pyplot as plt
from enum import Enum, auto
from scipy.stats import pointbiserialr, pearsonr, spearmanr


def visualize_explained_variance(X_proc: np.ndarray) -> None:
    """
    Plots cumulative explained variance to help choose the optimal number of PCA components.
    Avoid blindly inflating PCA components as might not significantly improve performance beyond a certain level.
    """
    pca = PCA()
    pca.fit(X_proc)

    cum_var = np.cumsum(pca.explained_variance_ratio_)
    plt.figure(figsize=(8, 5))
    plt.plot(range(1, len(cum_var) + 1), cum_var, marker='o', linestyle='--')
    plt.axhline(y=0.95, color='red', linestyle=':', label="95% variance")
    plt.title("Cumulative Explained Variance by PCA Components")
    plt.xlabel("Number of Components")
    plt.ylabel("Explained Variance")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def visualize_pca_clusters(X_pca: np.ndarray, labels: np.ndarray) -> None:
    """
    Visualizes clusters in 2D PCA space.
    """
    plt.figure(figsize=(10, 6))
    for cluster_id in np.unique(labels):
        idx = labels == cluster_id
        plt.scatter(X_pca[idx, 0], X_pca[idx, 1], label=f"Cluster {cluster_id}", alpha=0.6)
    plt.title("PCA-reduced Clusters")
    plt.xlabel("PCA Component 1")
    plt.ylabel("PCA Component 2")
    plt.legend()
    plt.grid(True)
    plt.show()


def visualize_prediction_errors(results_df: pd.DataFrame) -> None:
    """
    Plots actual vs. predicted prices with a reference diagonal.
    """
    plt.figure(figsize=(8, 5))
    plt.scatter(results_df["Actual"], results_df["Predicted"], alpha=0.6)
    plt.plot([results_df["Actual"].min(), results_df["Actual"].max()],
             [results_df["Actual"].min(), results_df["Actual"].max()],
             color='red', linestyle='--')
    plt.title("Actual vs. Predicted Prices")
    plt.xlabel("Actual Price")
    plt.ylabel("Predicted Price")
    plt.grid(True)
    plt.show()


pio.renderers.default = 'browser' # Non-Jupyter Rendering

class ChangeMethod(Enum):
    ABSOLUTE = "absolute"
    PERCENT = "percent"
    LOG = "log"
    MEAN = "mean"
    MEDIAN = "median"

class GraphType(Enum):
    BAR = "bar"
    SCATTER = "scatter"
    VIOLIN = "violin"


def draw_box_plots(df: pd.DataFrame, column_x: str, column_y: str):
    r, p_value = pointbiserialr(df['Duration == Monthly'], df[ROOMS])
    logging.info(f"Point Biserial Correlation {r} with p-value {p_value}")
    sns.boxplot(data=df, x=column_x, y=column_y)
    plt.title(f'{column_x} vs {column_y}')
    plt.xlabel(column_x)
    plt.ylabel(column_y)
    plt.tight_layout()
    plt.show()


def compute_change(series: pd.Series, method: ChangeMethod) -> float:
    f = pd.to_numeric(series.iloc[0], errors="coerce")
    l = pd.to_numeric(series.iloc[-1], errors="coerce")
    match method:
        case ChangeMethod.ABSOLUTE:
            return l - f
        case ChangeMethod.PERCENT:
            return np.nan if f == 0 else (l - f) / f
        case ChangeMethod.LOG:
            return np.nan if f <= 0 or l <= 0 else np.log(l / f)
        case ChangeMethod.MEAN:
            return series.mean()
        case ChangeMethod.MEDIAN:
            return series.median()
        case _:
            raise ValueError(f"Invalid ChangeMethod: {method}")


def compute_group_changes(df: pd.DataFrame, method: ChangeMethod, group_columns: list[str]) -> pd.DataFrame:
    # If method is MEAN or MEDIAN, compute directly per group
    if method in {ChangeMethod.MEAN, ChangeMethod.MEDIAN}:
        agg_type = "mean" if method == ChangeMethod.MEAN else "median"
        logging.info("Computing Aggregate Average Stats")
        changes = (
            # Ignore street level subgroups. Use point-level distribution
            df.groupby(group_columns, observed=True)[MONTHLY_USD_PRICE]
            .agg([agg_type, "std", "count"])
            .reset_index()
            .rename(columns={agg_type: PRICE_CHANGE, "std": "StdDev", "count": "Count"})
        )
    else:
        # Otherwise compute the chronological change within STREET subgroups and aggregate upwards
        changes = (
            df.groupby(group_columns + [STREET], observed=True)
            .apply(lambda group: compute_change(group.sort_values(DATE)[MONTHLY_USD_PRICE], method))
            .reset_index(name=PRICE_CHANGE)
        )
    return changes


def get_representative_samples(
    df: pd.DataFrame,
    group_cols: list[str],
    max_per_group: int | None = None,
    min_required: int = 0
) -> pd.DataFrame:
    samples = []
    for keys, group in df.groupby(group_cols, observed=True):

        if len(group) < min_required:
            continue  # skip undersized groups

        # Sample if max_per_group
        if max_per_group is not None:
            group = group.sample(n=min(len(group), max_per_group), random_state=42)

        # Reattach
        if isinstance(keys, tuple):
            for col, val in zip(group_cols, keys):
                group[col] = val
        else:
            group[group_cols[0]] = keys

        samples.append(group)

    return pd.concat(samples, ignore_index=True)


def build_hover_data(df: pd.DataFrame, change_type: str, group_columns: list[str]) -> dict:
    hover = {}
    if group_columns[0] == ROOMS:
        return {ROOMS: True}
    if PRICE_CHANGE in df.columns:
        hover[PRICE_CHANGE] = ':.1%' if change_type == "percent" else ':.2f'
    for col in [PROVINCE, ADMINISTRATIVE_UNIT, DISTANCE_FROM_CENTRE, "Count", PLACE]:
        if col in df.columns:
            hover[col] = ':.2f' if col == DISTANCE_FROM_CENTRE else True
    return hover

def build_bar_plots(df, x_axis, label, change_type) -> go.Figure:

    bar_df = df[[x_axis, PRICE_CHANGE, 'StdDev', 'Count']].drop_duplicates()
    bar_df.columns = [x_axis, 'mean_price', 'std_price', 'Count']

    bar_df[x_axis] = pd.Categorical(bar_df[x_axis], categories=df[x_axis].cat.categories, ordered=True)

    # Build hover data only from columns present
    hover_data = {
        'mean_price': ':.1%' if change_type == ChangeMethod.PERCENT else ':.2f',
        'std_price': ':.2f',
        'Count': True
    }

    texttemplate = '%{y:.1f}%' if change_type == ChangeMethod.PERCENT else '%{y:.2f}'

    fig = px.bar(
        bar_df,
        x=x_axis,
        y='mean_price',
        hover_data=hover_data,
        title=f"Rental Price by {x_axis}",
        labels={'mean_price': label, x_axis: x_axis}
    )

    fig.add_trace(go.Bar(
        x=bar_df[x_axis],
        y=bar_df['mean_price'],
        error_y=dict(type='data', array=bar_df['std_price'], visible=True),
        name='Price',
        marker_color='indigo',
        text=bar_df['mean_price'],
        textposition='outside'
    ))

    fig.update_traces(
        texttemplate=texttemplate,
        textposition='outside',
        marker_color='indigo',
    )
    fig.update_layout(xaxis=dict(categoryorder='array', categoryarray=bar_df[x_axis].cat.categories.tolist()))
    return fig


def build_violin_plots(df, x_axis, label, hover_data) -> go.Figure:
    fig = px.violin(
        df,
        x=x_axis,
        y=label,
        box=True,
        points="all",
        hover_name=x_axis,
        hover_data=hover_data,
        title=f"Rental Price by {x_axis}",
        labels={label: label, x_axis: x_axis},
        color_discrete_sequence=["indigo"]
    )
    fig.update_layout(xaxis=dict(categoryorder='array', categoryarray=df[x_axis].cat.categories.tolist()))
    return fig


def build_scatter_plots(
    df,
    x_axis,
    y_col,
    label,
    hover_data,
    by_distance=False,
    change_method: Optional[ChangeMethod] = None,
) -> go.Figure:
    logging.info(f"label: {label} x_axis: {x_axis}")

    x_vals = df[DISTANCE_FROM_CENTRE] if by_distance else df[x_axis]
    y_vals = df[y_col]

    fig = px.scatter(
        df,
        x=x_vals,
        y=y_vals,
        hover_name=x_axis,
        hover_data=hover_data,
        labels={y_col: label, x_axis: x_axis},
        title=f"Rental Price by {x_axis}",
        error_y="StdDev" if change_method else None,
        trendline="ols"
    )
    fig.update_traces(marker=dict(size=8, opacity=0.7, color='indigo'))

    if y_col != ROOMS and pd.api.types.is_categorical_dtype(df[x_axis]):
        fig.update_layout(
            xaxis=dict(
                categoryorder='array',
                categoryarray=df[x_axis].cat.categories.tolist()
            )
        )

    try:
        # Clean numeric data
        x_num = pd.to_numeric(x_vals, errors='coerce')
        y_num = pd.to_numeric(y_vals, errors='coerce')
        mask = x_num.notnull() & y_num.notnull()
        x_fit, y_fit = x_num[mask], y_num[mask]

        # Core metrics
        pearson_r, pearson_p = pearsonr(x_fit, y_fit)
        spearman_r, spearman_p = spearmanr(x_fit, y_fit)

        metrics_text = (
            f"Pearson r = {pearson_r:.2f} (p = {pearson_p:.2f})<br>"
            f"Spearman r = {spearman_r:.2f} (p = {spearman_p:.2f})<br>"
        )

        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.05, y=0.95,
            text=metrics_text,
            showarrow=False,
            align="left",
            font=dict(size=12),
            bgcolor="white",
            bordercolor="gray",
            borderwidth=1
        )

    except Exception as e:
        logging.warning(e)

    return fig


YEREVAN_CENTRE = (40.1792, 44.4991) # Latitude Longitude

def run_column_checks(df: pd.DataFrame, required_columns: list[str]):

    prior_length = len(df)
    column_checks = []

    for col in required_columns:
        column_checks.append((df[col].isnull()) | (df[col] == ""))

    missing_mask = reduce(operator.or_, column_checks) if column_checks else pd.Series(False, index=df.index)

    excluded_rows = df[missing_mask]
    logging.info(f"Excluded {len(excluded_rows)} of {prior_length} rows with missing {required_columns}")

    df = df[~missing_mask]

    return df



def prepare_visualization_data(
    df: pd.DataFrame,
    group_columns: list[str],
    change_method: Optional[ChangeMethod],
    min_sample: int = None,
    max_sample: int = None,
    by_distance: bool = False,
) -> pd.DataFrame:
    
    required_columns = group_columns.copy()
    if change_method == ChangeMethod.PERCENT:
        required_columns.append(STREET)

    df = run_column_checks(df, required_columns)
    prior_length = len(df)

    if PROVINCE in group_columns or ADMINISTRATIVE_UNIT in group_columns:
        df = df.sort_values(by=group_columns + [DATE], ascending=True)

    if change_method: # Distribution needs to be visualize for Distance From Yerevan
        group_changes = compute_group_changes(df, change_method, group_columns)
        if change_method in {ChangeMethod.MEAN, ChangeMethod.MEDIAN}:
            agg_df = group_changes  # POINT LEVEL AGGREGATE MEDIAN OR MEAN with STD DEV
        else:
            # SUBGROUP BY STREET FOR PERCENT / ABSOLUTE CHANGE
            agg_df = (
                group_changes
                .groupby(group_columns, observed=True)[PRICE_CHANGE]
                .agg(['mean', 'std', 'count'])
                .reset_index()
                .rename(columns={'mean': PRICE_CHANGE, 'std': 'StdDev', 'count': 'Count'})
            )
        df = df.merge(agg_df, on=group_columns, how='left')
        df = df.dropna(subset=[PRICE_CHANGE, 'StdDev', 'Count'])
        logging.info(f"{len(df) - prior_length} rows were excluded with no group statistics or lacking more than one row for Datetime comparison")

    if min_sample or max_sample:
        # Ensure sample size meets the minimum and maximum size
        pre_sampling_length = len(df)
        df = get_representative_samples(df, group_columns, max_sample, min_sample)
        df["Count"] = df.groupby(group_columns, observed=True)[MONTHLY_USD_PRICE].transform("count")
        logging.info(f"Removed {pre_sampling_length - len(df)} of {pre_sampling_length} rows with a min max sample size of {min_sample} : {max_sample}")

    x_axis = group_columns[0] # Longitude Latitude

    if by_distance:
        if LATITUDE not in df.columns or LONGITUDE not in df.columns:
            raise ValueError("Latitude and Longitude required for distance calc.")
        df[DISTANCE_FROM_CENTRE] = df.apply(compute_distance, axis=1)
        x_axis = DISTANCE_FROM_CENTRE

    if set(group_columns) == {PROVINCE, ADMINISTRATIVE_UNIT}:
        df[PLACE] = df[group_columns].agg(" – ".join, axis=1)
        if not by_distance:
            x_axis = PLACE

    if not by_distance and group_columns == [PROVINCE]:
        x_axis = PROVINCE

    if PROVINCE or ADMINISTRATIVE_UNIT in group_columns:
        order_col = MONTHLY_USD_PRICE if not change_method else PRICE_CHANGE
        order = df.groupby(x_axis, observed=True)[order_col].median().sort_values().index.tolist()
        df[x_axis] = pd.Categorical(df[x_axis], categories=order, ordered=True)

    if change_method == ChangeMethod.PERCENT:
        df[PRICE_CHANGE] *= 100

    return df, x_axis


def visualize_price_stats(
    df: pd.DataFrame,
    group_columns: list[str],
    change_method: Optional[ChangeMethod],
    graph_type: GraphType,
    by_distance: bool = False,
    min_sample=None,
    max_sample=None,
):

    df, x_axis = prepare_visualization_data(df, group_columns, change_method, min_sample, max_sample, by_distance)

    if GraphType != GraphType.SCATTER:
        by_distance = False

    label_map = {
        ChangeMethod.ABSOLUTE: "Price Change (USD)",
        ChangeMethod.PERCENT: "Price Change (%)",
        ChangeMethod.LOG: "Log Price Change",
        ChangeMethod.MEAN: "Average Price",
        ChangeMethod.MEDIAN: "Average Price",
    }

    label = label_map.get(change_method, "Monthly USD Price")
    y_col = PRICE_CHANGE if change_method else MONTHLY_USD_PRICE
    hover_data = build_hover_data(df, change_method, group_columns)

    fig = None
    match graph_type:
        case GraphType.SCATTER:
            fig = build_scatter_plots(df, x_axis, y_col, label, hover_data, by_distance, change_method)
        case GraphType.VIOLIN:
            fig = build_violin_plots(df, x_axis, label, hover_data)
        case GraphType.BAR:
            fig = build_bar_plots(df, x_axis, label, change_method)  # Note: you’ll want change_type here to fix hover

    if fig:
        fig.update_layout(template='plotly_white', dragmode='zoom', hovermode='closest', xaxis_tickangle=45)
        fig.show(config={'scrollZoom': True})



class VisualizationPreset(Enum):
    DISTANCE_FROM_YEREVAN = auto()
    ADMIN_UNITS_MEDIAN = auto()
    PERCENT_CHANGE_ADMIN_WITH_STREETWISE_DEVIATION = auto()
    CORRELATION_ROOMS_DURATION = auto()
    CORRELATION_PROPERTY_FEATURES = auto()
    BOX_PLOTS = auto()
    ROOMS_V_PRICE = auto()


if __name__ == "__main__":

    # python -m scripts.analytics.visual

    from scripts.load import load

    PRESET = VisualizationPreset.CORRELATION_PROPERTY_FEATURES

    training, testing, addresses = load()
    df = pd.concat([training, testing], ignore_index=True)

    if PRESET == VisualizationPreset.DISTANCE_FROM_YEREVAN:
        visualize_price_stats(
            df,
            group_columns=[PROVINCE, ADMINISTRATIVE_UNIT],
            graph_type=GraphType.SCATTER,
            change_method=None,
            by_distance=True,
            min_sample=100,
        )

    elif PRESET == VisualizationPreset.ADMIN_UNITS_MEDIAN:
        visualize_price_stats(
            df,
            group_columns=[PROVINCE, ADMINISTRATIVE_UNIT],
            graph_type=GraphType.BAR,
            change_method=ChangeMethod.MEDIAN,
            min_sample=100,
        )

    elif PRESET == VisualizationPreset.PERCENT_CHANGE_ADMIN_WITH_STREETWISE_DEVIATION:
        visualize_price_stats(
            df,
            group_columns=[PROVINCE, ADMINISTRATIVE_UNIT],
            graph_type=GraphType.BAR,
            change_method=ChangeMethod.PERCENT,
            min_sample=100,
        )

    elif PRESET == VisualizationPreset.BOX_PLOTS: # Biserial
        df['Duration == Monthly'] = df[DURATION] == "Monthly"
        draw_box_plots(df, DURATION, MONTHLY_USD_PRICE)
        draw_box_plots(df, DURATION, ROOMS)

    elif PRESET == VisualizationPreset.ROOMS_V_PRICE:
        visualize_price_stats(
            df,
            group_columns=[ROOMS],
            graph_type=GraphType.SCATTER,
            min_sample=50,
            change_method=ChangeMethod.MEDIAN,
        )

    elif PRESET == VisualizationPreset.CORRELATION_ROOMS_DURATION:
        draw_correlation_matrix(df[[ROOMS, MONTHLY_USD_PRICE, 'Duration == Monthly']], binary_columns=['Duration == Monthly'])
        
    elif PRESET == VisualizationPreset.CORRELATION_PROPERTY_FEATURES:

        for ranking_column in [AMENITIES_RANK, PARKING_RANK, APPLIANCES_RANK]: # These are added in the processing stage

            ranking_mask = df[ranking_column] == 0  # Mask zero-ranked rows
            excluded_count = ranking_mask.sum()

            logging.info(f"Excluded {excluded_count} rows where {ranking_column} == 0")

            df = df[~ranking_mask]

            visualize_price_stats(
                df,
                group_columns=[ranking_column],
                graph_type=GraphType.SCATTER,
                min_sample=50,
                change_method=None,
            )

        draw_correlation_matrix(df[[MONTHLY_USD_PRICE, AMENITIES_RANK, APPLIANCES_RANK, PARKING_RANK]])



