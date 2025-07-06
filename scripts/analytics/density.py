import pandas as pd
import folium
from folium.plugins import HeatMap


def draw_price_density_map(training: pd.DataFrame, testing: pd.DataFrame):
    data = pd.concat([training, testing], ignore_index=True)

    data[['Latitude', 'Longitude', 'Price']] = data[['Latitude', 'Longitude', 'Price']].apply(pd.to_numeric, errors='coerce')
    data = data.dropna(subset=['Latitude', 'Longitude', 'Price'])

    days = 1
    data['Price'] = data['Price'] * days

    rental_map = folium.Map(
        location=[40.1792, 44.4991],
        zoom_start=12,
        tiles="CartoDB Positron"
    )

    heat_data = data[['Latitude', 'Longitude', 'Price']].values.tolist()

    HeatMap(heat_data).add_to(rental_map)

    rental_map.save('price_heatmap.html')
    print("Heatmap saved as 'rental_price_heatmap.html'")
