import pandas as pd
import numpy as np
import rasterio
import requests
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "training_dataset_large.csv"
MAPBIOMAS_TIF = PROJECT_ROOT / "data" / "raw" / "mapbiomas" / "chile_coverage_2022.tif"
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "training_dataset_large_spatial.csv"

def get_elevation_batch(coords):
    # Open-Meteo allows batching coordinates
    lats = ",".join([str(c[0]) for c in coords])
    lons = ",".join([str(c[1]) for c in coords])
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lats}&longitude={lons}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "elevation" in data:
                return data["elevation"]
    except Exception as e:
        print(f"Error fetching batch: {e}")
    return [np.nan] * len(coords)

def process_spatial_data():
    print("Cargando dataset base...")
    df = pd.read_csv(INPUT_CSV)
    print(f"Dataset cargado con {len(df)} filas. Iniciando cruce espacial...")
    
    # 1. Elevación (usando batching en grupos de 100)
    print("Obteniendo elevaciones usando Open-Meteo API en lotes...")
    elevations = []
    batch_size = 100
    for i in range(0, len(df), batch_size):
        chunk = df.iloc[i:i+batch_size]
        coords = list(zip(chunk['Latitud'], chunk['Longitud']))
        elevations.extend(get_elevation_batch(coords))
        if i % 1000 == 0:
            print(f"  Elevaciones: {i}/{len(df)} procesadas...")
        time.sleep(0.5) # Respetar rate limits
        
    df['elevation'] = elevations
    
    # 2. Uso de suelo (MapBiomas)
    print("Extrayendo clases de uso de suelo (MapBiomas) del GeoTIFF...")
    try:
        with rasterio.open(MAPBIOMAS_TIF) as src:
            land_cover = []
            for i, row in df.iterrows():
                coord = [(row['Longitud'], row['Latitud'])]
                try:
                    val = next(src.sample(coord))[0]
                    land_cover.append(val)
                except:
                    land_cover.append(np.nan)
                if i % 1000 == 0:
                    print(f"  MapBiomas: {i}/{len(df)} procesadas...")
                    
            df['land_cover_class'] = land_cover
    except Exception as e:
        print(f"Error abriendo archivo MapBiomas: {e}")
        df['land_cover_class'] = np.nan
        
    print(f"Dataset espacial generado con {len(df)} muestras.")
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Guardado exitosamente en: {OUTPUT_CSV}")

if __name__ == "__main__":
    process_spatial_data()
