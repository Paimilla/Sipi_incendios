import pandas as pd
import numpy as np
import srtm
import math
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "training_dataset_large_v3a.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "training_dataset_large_v3b.csv"

def calculate_topography():
    print("Cargando dataset V3A...")
    df = pd.read_csv(INPUT_CSV)
    
    print("Inicializando base de datos SRTM de la NASA (descargará tiles de Chile automáticamente)...")
    elevation_data = srtm.get_data()
    
    elevations = []
    slopes = []
    aspects = []
    
    d = 0.0003  # Aprox 30 metros en grados
    total = len(df)
    
    print("Calculando Elevación, Pendiente y Orientación para todos los incendios...")
    for i, row in df.iterrows():
        lat = row['Latitud']
        lon = row['Longitud']
        
        # Obtener elevación central
        elev = elevation_data.get_elevation(lat, lon)
        if elev is None:
            elevations.append(np.nan)
            slopes.append(np.nan)
            aspects.append(np.nan)
            continue
            
        # Obtener vecinos (N, S, E, W)
        elev_n = elevation_data.get_elevation(lat + d, lon)
        elev_s = elevation_data.get_elevation(lat - d, lon)
        elev_e = elevation_data.get_elevation(lat, lon + d)
        elev_w = elevation_data.get_elevation(lat, lon - d)
        # Fallback a elevacion central si el vecino no tiene dato
        if elev_n is None: elev_n = elev
        if elev_s is None: elev_s = elev
        if elev_e is None: elev_e = elev
        if elev_w is None: elev_w = elev
        
        # Distancia física en metros
        d_lat_m = d * 111320.0
        d_lon_m = d * 111320.0 * math.cos(math.radians(lat))
        
        # Gradientes
        dz_dx = (elev_e - elev_w) / (2.0 * d_lon_m) if d_lon_m != 0 else 0
        dz_dy = (elev_n - elev_s) / (2.0 * d_lat_m)
        
        # Pendiente (Slope)
        slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
        slope_deg = math.degrees(slope_rad)
        
        # Orientación (Aspect) 0=N, 90=E, 180=S, 270=W
        if dz_dx == 0 and dz_dy == 0:
            aspect_deg = -1 # Plano
        else:
            aspect_rad = math.atan2(dz_dx, dz_dy)
            aspect_deg = (math.degrees(aspect_rad) + 360) % 360
            
        elevations.append(elev)
        slopes.append(slope_deg)
        aspects.append(aspect_deg)
        
        if (i+1) % 1000 == 0:
            print(f"  Procesados {i+1}/{total}...")
            
    df['elevation'] = elevations
    df['slope_deg'] = slopes
    df['aspect_deg'] = aspects
    
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nGuardado exitosamente en: {OUTPUT_CSV}")
    print("Muestra de estadísticas de Topografía:")
    print(df[['elevation', 'slope_deg', 'aspect_deg']].describe())

if __name__ == "__main__":
    calculate_topography()
