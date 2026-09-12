import os
import glob
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "itrend_registro_historico" / "data"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "itrend_incendios_historicos.csv"

def merge_itrend_data():
    csv_files = glob.glob(os.path.join(INPUT_DIR, "*/*.csv"))
    
    if not csv_files:
        print("No se encontraron archivos CSV de Itrend.")
        return

    all_data = []
    
    for file in csv_files:
        print(f"Leyendo {os.path.basename(file)}...")
        try:
            # Los archivos de Itrend usan '|' como separador y codificación latin-1 o utf-8
            df = pd.read_csv(file, sep='|', encoding='latin-1')
            all_data.append(df)
        except Exception as e:
            print(f"Error procesando {file}: {e}")

    if all_data:
        print("\nConcatenando todos los años...")
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Limpiar nombres de columnas (eliminar caracteres raros)
        final_df.columns = [col.encode('latin-1').decode('utf-8', 'ignore') if isinstance(col, str) else col for col in final_df.columns]
        
        print(f"Total de registros históricos de incendios: {len(final_df)}")
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        final_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        print(f"Datos combinados guardados en: {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_itrend_data()
