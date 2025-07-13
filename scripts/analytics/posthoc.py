import pandas as pd
import seaborn as sns
import scikit_posthocs as sp
import plotly.io as pio
from pingouin import compute_effsize
from itertools import combinations
from matplotlib import pyplot as plt

pio.renderers.default = 'browser' # Non-Jupyter Rendering

def dunn_posthoc(df: pd.DataFrame, value_col: str, col1: str, col2: str):

    df["FurnBal"] = df[col1].astype(str) + "_" + df[col2].astype(str)

    # Run PostHoc Analysis
    posthoc = sp.posthoc_dunn(
        df,
        val_col=value_col,
        group_col="FurnBal",
        p_adjust='bonferroni'
    )

    # p-values with significance levels
    def p_to_label(p):
        if p < 0.001:
            return "P < 0.001\nVERY SIGNIFICANT"
        elif p < 0.01:
            return "P < 0.01"
        elif p < 0.05:
            return "P < 0.05"
        else:
            return "NOT SIGNIFICANT"

    annotations = posthoc.copy().astype(str)

    testing_combinations = list(combinations(df["FurnBal"].unique(), 2))

    for g1, g2 in testing_combinations:
        group1 = df[df["FurnBal"] == g1][value_col]
        group2 = df[df["FurnBal"] == g2][value_col]
        d = compute_effsize(group1, group2, eftype='cohen')  # EFFECT SIZE
        
        pval = posthoc.loc[g1, g2]
        label = f"{p_to_label(pval)}\nd={d:.3f}"
        
        annotations.loc[g1, g2] = label
        annotations.loc[g2, g1] = label

    sns.heatmap(posthoc.astype(float), annot=annotations, fmt="", cmap="coolwarm", cbar_kws={"label": "p-value"})
    plt.title("Dunn Significance & Cohen's d: USD Price by [Furniture, Balcony]")
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.show()