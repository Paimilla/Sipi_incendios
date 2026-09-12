import urllib.request
import os
import ssl
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "mapbiomas"
os.makedirs(OUTPUT_DIR, exist_ok=True)
FILE_PATH = OUTPUT_DIR / "chile_coverage_2022.tif"

URL = "https://storage.googleapis.com/mapbiomas-public/initiatives/chile/coverage/chile_coverage_2022.tif"

def download_mapbiomas():
    if os.path.exists(FILE_PATH):
        print(f"El archivo {FILE_PATH} ya existe.")
        return
        
    print(f"Iniciando descarga directa desde MapBiomas (esto tomará unos minutos, el archivo es grande)...")
    
    # Desactivar verificación estricta de SSL en caso de problemas corporativos
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        urllib.request.urlretrieve(URL, FILE_PATH)
        print("¡Descarga completada exitosamente!")
    except Exception as e:
        print(f"Error durante la descarga: {e}")

if __name__ == "__main__":
    download_mapbiomas()
