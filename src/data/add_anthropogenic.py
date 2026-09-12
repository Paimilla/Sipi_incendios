import pandas as pd
import numpy as np
import urllib.request
import zipfile
import os
from pathlib import Path
from sklearn.neighbors import BallTree

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INPUT_CSV = PROCESSED_DIR / "training_dataset_large_spatial.csv"
OUTPUT_CSV = PROCESSED_DIR / "training_dataset_large_v3a.csv"
GEONAMES_URL = "http://download.geonames.org/export/dump/CL.zip"
GEONAMES_ZIP = RAW_DIR / "CL.zip"
GEONAMES_TXT = RAW_DIR / "CL.txt"

def get_nearest_town_distance():
    print("Cargando dataset V2...")
    df = pd.read_csv(INPUT_CSV)
    
    if not os.path.exists(GEONAMES_TXT):
        print("Descargando base de datos de poblados de GeoNames (Chile)...")
        urllib.request.urlretrieve(GEONAMES_URL, GEONAMES_ZIP)
        with zipfile.ZipFile(GEONAMES_ZIP, 'r') as zip_ref:
            zip_ref.extractall(RAW_DIR)
            
    print("Leyendo poblados...")
    cols = ['geonameid', 'name', 'asciiname', 'alternatenames', 'latitude', 'longitude', 'feature_class', 'feature_code', 'country_code', 'cc2', 'admin1_code', 'admin2_code', 'admin3_code', 'admin4_code', 'population', 'elevation', 'dem', 'timezone', 'modification_date']
    places = pd.read_csv(GEONAMES_TXT, sep='\t', names=cols, low_memory=False)
    
    # Filtrar solo lugares poblados (feature_class == 'P')
    places = places[places['feature_class'] == 'P'].copy()
    print(f"Se encontraron {len(places)} poblados/asentamientos en Chile.")
    
    places_coords = np.vstack([places['latitude'], places['longitude']]).T
    places_rad = np.radians(places_coords)
    
    print("Construyendo KDTree esférico...")
    tree = BallTree(places_rad, metric='haversine')
    
    fire_coords = np.vstack([df['Latitud'], df['Longitud']]).T
    fire_rad = np.radians(fire_coords)
    
    print("Calculando distancia de cada incendio al poblado más cercano...")
    distances, _ = tree.query(fire_rad, k=1)
    
    # Convertir a kilómetros
    distances_km = distances.flatten() * 6371.0
    
    df['dist_nearest_town_km'] = distances_km
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Guardado exitosamente en: {OUTPUT_CSV}")
    print(f"Distancia media a poblado: {df['dist_nearest_town_km'].mean():.2f} km")

if __name__ == "__main__":
    get_nearest_town_distance()
