import os
import zipfile
import pandas as pd
import glob
import time
import re
from pathlib import Path

# Directorios
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "viirs_raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "viirs_chile"

def process_viirs_zips():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    zip_files = glob.glob(os.path.join(INPUT_DIR, "viirs-snpp_*_all_countries.zip"))
    
    if not zip_files:
        print("No se encontraron archivos ZIP de VIIRS.")
        return

    all_chile_data = []

    for zip_path in sorted(zip_files):
        print(f"Procesando {os.path.basename(zip_path)}...")
        start_time = time.time()
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Buscar específicamente el archivo de Chile
                csv_files = [f for f in z.namelist() if 'Chile' in f and f.endswith('.csv')]
                for csv_file in csv_files:
                    print(f"  Leyendo {csv_file}...")
                    with z.open(csv_file) as f:
                        df = pd.read_csv(f)
                        if not df.empty:
                            all_chile_data.append(df)
        except Exception as e:
            print(f"Error procesando {zip_path}: {e}")
            
        print(f"  Tiempo: {time.time() - start_time:.2f}s")
        
    if all_chile_data:
        print("\nConcatenando todos los datos filtrados...")
        final_df = pd.concat(all_chile_data, ignore_index=True)
        print(f"Total de registros de Chile encontrados: {len(final_df)}")
        
        output_file = os.path.join(OUTPUT_DIR, "viirs_chile_2017_2024.csv")
        final_df.to_csv(output_file, index=False)
        print(f"Datos guardados exitosamente en: {output_file}")
    else:
        print("No se encontraron datos de Chile.")

if __name__ == "__main__":
    process_viirs_zips()
