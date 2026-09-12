"""
Punto de entrada principal para la aplicación web SIpi Incendios.
Permite ejecutar el servidor tanto en local como en plataformas cloud (Render, Railway, Heroku, etc.).
"""
import os
import sys
from pathlib import Path

# Configurar ruta base del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Importar la app Flask desde el módulo del dashboard
from dashboard.server import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')
    print(f"Iniciando SIpi Dashboard en el puerto {port} (debug={debug})...")
    app.run(host='0.0.0.0', port=port, debug=debug)
