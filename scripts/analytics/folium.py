import logging, webbrowser, folium
import pandas as pd
from pathlib import Path
from scripts.csv_columns import *
from folium.plugins import HeatMap


def rental_rates_density_map(df: pd.DataFrame):

    logging.info("Launching Folium")

    df[[LATITUDE, LONGITUDE, MONTHLY_USD_PRICE]] = df[[LATITUDE, LONGITUDE, MONTHLY_USD_PRICE]].apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=[LATITUDE, LONGITUDE, MONTHLY_USD_PRICE])

    data_series: list[list[float]] = df[[LATITUDE, LONGITUDE, MONTHLY_USD_PRICE]].values.tolist()

    filepath = Path("Rental Rate Density.html")

    folium_map = folium.Map(
        location=[40.1792, 44.4991],
        zoom_start=12,
        tiles="CartoDB Positron" # English TileMap
    )

    HeatMap(data_series).add_to(folium_map)
    folium_map.save(filepath)
    webbrowser.open(filepath.resolve().as_uri())



if __name__ == '__main__':

    # python -m scripts.analytics.folium

    from scripts.load import load
    training, testing, addresses = load()
    df = pd.concat([training, testing], ignore_index=True)

    rental_rates_density_map(df)
