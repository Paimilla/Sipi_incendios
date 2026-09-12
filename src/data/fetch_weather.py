import requests
import pandas as pd
from datetime import timedelta, datetime
import time

def fetch_weather_for_fire(lat, lon, fire_date_str, window_days_before=7):
    """
    Obtiene datos meteorológicos históricos de Open-Meteo para un punto y fecha dados.
    Extrae la data desde `window_days_before` días antes del incendio hasta el día del incendio.
    
    Args:
        lat (float): Latitud
        lon (float): Longitud
        fire_date_str (str): Fecha del incendio en formato 'YYYY-MM-DD'
        window_days_before (int): Número de días previos a analizar
        
    Returns:
        dict: Diccionario con features agregadas (promedios, máximos, acumulados)
    """
    fire_date = datetime.strptime(fire_date_str, '%Y-%m-%d')
    start_date = (fire_date - timedelta(days=window_days_before)).strftime('%Y-%m-%d')
    
    # Parámetros de la API de Open-Meteo (Archive)
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": fire_date_str,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,soil_temperature_0_to_7cm,soil_moisture_0_to_7cm",
        "timezone": "America/Santiago"
    }
    
    # Retry mechanism
    for attempt in range(3):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            break
        except requests.exceptions.RequestException as e:
            if attempt == 2:
                print(f"Error fetching data for lat={lat}, lon={lon}, date={fire_date_str}: {e}")
                return None
            time.sleep(2)
            
    if "hourly" not in data:
        return None
        
    df = pd.DataFrame(data["hourly"])
    df['time'] = pd.to_datetime(df['time'])
    
    # Separar en dos periodos: "previo" (hasta el día anterior) y "día del incendio"
    # Para simplificar, calculamos features globales de la ventana
    
    features = {
        "temp_max_window": df['temperature_2m'].max(),
        "temp_mean_window": df['temperature_2m'].mean(),
        "humidity_min_window": df['relative_humidity_2m'].min(),
        "humidity_mean_window": df['relative_humidity_2m'].mean(),
        "precip_acc_window": df['precipitation'].sum(),
        "wind_speed_max_window": df['wind_speed_10m'].max(),
        "wind_speed_mean_window": df['wind_speed_10m'].mean(),
        "soil_temp_mean": df['soil_temperature_0_to_7cm'].mean(),
        "soil_moisture_mean": df['soil_moisture_0_to_7cm'].mean()
    }
    
    # Extraer específicamente las condiciones del día del incendio (asumimos 14:00 PM como hora crítica)
    fire_day_data = df[df['time'].dt.date == fire_date.date()]
    if not fire_day_data.empty:
        # Aproximación a las 14:00 o máximo del día
        features["temp_fire_day_max"] = fire_day_data['temperature_2m'].max()
        features["humidity_fire_day_min"] = fire_day_data['relative_humidity_2m'].min()
        features["wind_fire_day_max"] = fire_day_data['wind_speed_10m'].max()
    else:
        features["temp_fire_day_max"] = None
        features["humidity_fire_day_min"] = None
        features["wind_fire_day_max"] = None

    return features

# Ejemplo de uso
if __name__ == "__main__":
    print("Prueba de API Open-Meteo...")
    res = fetch_weather_for_fire(-35.42, -71.65, "2023-02-02", window_days_before=7)
    if res:
        for k, v in res.items():
            print(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")
