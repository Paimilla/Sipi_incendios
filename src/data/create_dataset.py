import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import concurrent.futures
import time
import requests
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "itrend_incendios_historicos.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "training_dataset_large.csv"

# Constantes (Límite Open-Meteo gratuito es ~10,000 peticiones/día)
SAMPLE_SIZE = 4500  # 4500 positivos + 4500 negativos = 9000 total

def fetch_weather(lat, lon, date_str, label, idx):
    """
    Obtiene datos meteorológicos.
    """
    try:
        fire_date = datetime.strptime(str(date_str).split()[0], '%Y-%m-%d')
    except Exception:
        # Algunos formatos pueden venir como DD-MM-YYYY
        try:
            fire_date = datetime.strptime(str(date_str).split()[0], '%d-%m-%Y')
        except:
            return None
            
    start_date = (fire_date - timedelta(days=7)).strftime('%Y-%m-%d')
    fire_date_str = fire_date.strftime('%Y-%m-%d')
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": fire_date_str,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,soil_temperature_0_to_7cm,soil_moisture_0_to_7cm",
        "timezone": "America/Santiago"
    }
    
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "hourly" in data:
                    df = pd.DataFrame(data["hourly"])
                    df['time'] = pd.to_datetime(df['time'])
                    
                    features = {
                        "id": idx,
                        "Latitud": lat,
                        "Longitud": lon,
                        "Fecha": fire_date_str,
                        "temp_max_window": df['temperature_2m'].max(),
                        "temp_mean_window": df['temperature_2m'].mean(),
                        "humidity_min_window": df['relative_humidity_2m'].min(),
                        "humidity_mean_window": df['relative_humidity_2m'].mean(),
                        "precip_acc_window": df['precipitation'].sum(),
                        "wind_speed_max_window": df['wind_speed_10m'].max(),
                        "wind_speed_mean_window": df['wind_speed_10m'].mean(),
                        "soil_temp_mean": df['soil_temperature_0_to_7cm'].mean(),
                        "soil_moisture_mean": df['soil_moisture_0_to_7cm'].mean(),
                        "Fire_Probability": label
                    }
                    return features
            break
        except Exception:
            time.sleep(1)
            
    return None

def random_date(start_year=2010, end_year=2023):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def main():
    print(f"Cargando {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    # Limpiar columnas
    df['Latitud'] = pd.to_numeric(df['Latitud'], errors='coerce')
    df['Longitud'] = pd.to_numeric(df['Longitud'], errors='coerce')
    
    # Filtrar válidos (solo Chile continental aprox)
    valid_fires = df.dropna(subset=['Latitud', 'Longitud', 'Fecha']).copy()
    valid_fires = valid_fires[
        (valid_fires['Latitud'] >= -56.0) & (valid_fires['Latitud'] <= -17.0) &
        (valid_fires['Longitud'] >= -76.0) & (valid_fires['Longitud'] <= -66.0)
    ]
    
    print(f"Total incendios con coordenadas válidas: {len(valid_fires)}")
    
    # 1. Muestras Positivas
    positives = valid_fires.sample(n=SAMPLE_SIZE, random_state=42)
    positives['label'] = 1
    
    # 2. Muestras Negativas (mismas coordenadas de incendios, pero fechas aleatorias)
    negatives = valid_fires.sample(n=SAMPLE_SIZE, random_state=99).copy()
    negatives['Fecha'] = negatives['Fecha'].apply(lambda x: random_date().strftime('%Y-%m-%d'))
    negatives['label'] = 0
    
    combined = pd.concat([positives, negatives]).reset_index(drop=True)
    
    print(f"Iniciando descarga de clima para {len(combined)} muestras usando multithreading...")
    
    # Escribir encabezado al archivo de salida
    pd.DataFrame(columns=[
        'id', 'Latitud', 'Longitud', 'Fecha', 'temp_max_window', 'temp_mean_window',
        'humidity_min_window', 'humidity_mean_window', 'precip_acc_window', 
        'wind_speed_max_window', 'wind_speed_mean_window', 'soil_temp_mean', 
        'soil_moisture_mean', 'Fire_Probability'
    ]).to_csv(OUTPUT_FILE, index=False)
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(
                fetch_weather, row['Latitud'], row['Longitud'], row['Fecha'], row['label'], idx
            ): idx for idx, row in combined.iterrows()
        }
        
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
            completed += 1
            
            # Guardar progresivamente cada 100 resultados
            if len(results) >= 100:
                pd.DataFrame(results).to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
                results = []
                
            if completed % 100 == 0:
                print(f"  {completed}/{len(combined)} procesados...")

    # Guardar cualquier remanente
    if results:
        pd.DataFrame(results).to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
        
    final_df = pd.read_csv(OUTPUT_FILE)
    print(f"\nDataset final creado con {len(final_df)} filas.")
    print(f"Positivos (1): {len(final_df[final_df['Fire_Probability'] == 1])}")
    print(f"Negativos (0): {len(final_df[final_df['Fire_Probability'] == 0])}")
    
    print(f"Guardado exitosamente en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
