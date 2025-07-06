import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def assign_price_change_coordinates(df: pd.DataFrame):
    df['Price'] = df['Price'] * 30
    df = df.sort_values(['Longitude', 'Latitude', 'Datetime'])
    df['Price_Change'] = df.groupby(['Longitude', 'Latitude'])['Price'].pct_change() * 100
    df = df.dropna(subset='Price_Change')
    return df


def ensure_numeric(df: pd.DataFrame):
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    return df


def plot_actual_vs_predicted_coords(X, y_true, y_pred, title='Prediction vs. Actual'):
    plt.figure(figsize=(12, 5))

    # Predicted values
    plt.subplot(1, 2, 1)
    scatter1 = plt.scatter(X['Longitude'], X['Latitude'], c=y_pred, cmap='coolwarm', s=40, edgecolor='k')
    plt.colorbar(scatter1, label='Predicted % Change')
    plt.title(f'{title}: Predicted')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True)

    # Actual values
    plt.subplot(1, 2, 2)
    scatter2 = plt.scatter(X['Longitude'], X['Latitude'], c=y_true, cmap='coolwarm', s=40, edgecolor='k')
    plt.colorbar(scatter2, label='Actual % Change')
    plt.title(f'{title}: Actual')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True)

    plt.tight_layout()
    plt.show()


def run_geoocoord_prediction_model(training: pd.DataFrame, testing: pd.DataFrame):

    training = assign_price_change_coordinates(training)
    testing = assign_price_change_coordinates(testing)

    training = ensure_numeric(training)
    testing = ensure_numeric(testing)

    X_train = training[['Longitude', 'Latitude']]
    y_train = training['Price_Change']

    X_test = testing[['Longitude', 'Latitude']]
    y_test = testing['Price_Change']

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"Mean Absolute Error: {mae:.2f}")
    print(f"Mean Squared Error: {mse:.2f}")
    print(f"R² Score: {r2:.2f}")

    y_pred_test = model.predict(X_test)
    plot_actual_vs_predicted_coords(X_test, y_test, y_pred_test, title='Testing Set')




