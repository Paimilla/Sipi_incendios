"""
Configuración central del proyecto SIpi Incendios.
Todas las rutas se calculan relativamente a la raíz del proyecto.
"""
from pathlib import Path

# Raíz del proyecto (2 niveles arriba de este archivo: src/config.py → src/ → proyecto/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directorios de datos
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Archivos de datos clave
ITREND_CSV = PROCESSED_DIR / "itrend_incendios_historicos.csv"
MAPBIOMAS_TIF = RAW_DIR / "mapbiomas" / "chile_coverage_2022.tif"
GEONAMES_ZIP = RAW_DIR / "CL.zip"
GEONAMES_TXT = RAW_DIR / "CL.txt"

# Datasets de entrenamiento
DATASET_CLIMA = PROCESSED_DIR / "training_dataset_large.csv"
DATASET_SPATIAL = PROCESSED_DIR / "training_dataset_large_spatial.csv"
DATASET_V3A = PROCESSED_DIR / "training_dataset_large_v3a.csv"
DATASET_V3B = PROCESSED_DIR / "training_dataset_large_v3b.csv"
DATASET_FINAL = PROCESSED_DIR / "training_dataset_final.csv"

# Modelos
MODELS_DIR = PROJECT_ROOT / "src" / "models"
FINAL_MODEL_PATH = MODELS_DIR / "xgboost_fire_model_final.pkl"

# Constantes geográficas de Chile continental
CHILE_LAT_MIN = -56.0
CHILE_LAT_MAX = -17.0
CHILE_LON_MIN = -76.0
CHILE_LON_MAX = -66.0

# Clases de MapBiomas quemables (bosques, matorrales, pastizales, plantaciones)
BURNABLE_CLASSES = [3, 4, 5, 9, 11, 12, 15, 21, 39, 41]
