# SIpi Incendios — Sistema Inteligente de Predicción de Incendios Forestales (Chile)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Model](https://img.shields.io/badge/Model-XGBoost%20V2-orange.svg)](https://xgboost.readthedocs.io/)
[![ROC-AUC](https://img.shields.io/badge/ROC--AUC-0.7932-green.svg)]()
[![F1-Score](https://img.shields.io/badge/F1--Score-0.7515-green.svg)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg)]()
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

**SIpi Incendios** es una plataforma integral de Machine Learning y análisis geoespacial diseñada para predecir, proyectar y simular el riesgo de incendios forestales en Chile continental. Integra registros históricos oficiales de CONAF e Itrend (2002–2023), capas de cobertura vegetal de **MapBiomas Chile 2022**, topografía digital **NASA SRTM**, datos de asentamientos humanos de **GeoNames**, modelos meteorológicos en tiempo real vía **Open-Meteo API** y explicabilidad local mediante **SHAP**.

---

## 🌐 Despliegue Online en la Nube (Visualizador Web)

El proyecto está 100% preparado para ser desplegado como servicio web interactivo gratuito en **Render.com**, **Railway** o **Hugging Face Spaces**, sin necesidad de configurar bases de datos ni claves de API:

### Opción A: Despliegue Rápido en Render.com (Gratis)
1. Haz un **Fork** o sube este repositorio a tu cuenta de GitHub.
2. Inicia sesión en [Render.com](https://render.com) y crea un nuevo **Web Service**.
3. Conecta tu repositorio de GitHub.
4. Render detectará automáticamente el archivo `render.yaml` o configura manualmente:
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 2 --timeout 120`
5. Haz clic en **Create Web Service**. En 2 minutos tendrás una URL pública para compartir el visualizador en vivo con cualquier persona.

### Opción B: Despliegue en Railway / Hugging Face Spaces
El repositorio incluye un `Procfile` estándar (`web: gunicorn app:app --workers 2 --timeout 120`) compatible con cualquier plataforma PaaS de contenedores Python.

---

## 🏗️ Arquitectura del Repositorio

```
SIpi incendios/
├── app.py                            # Entrypoint principal de producción (Gunicorn / Local)
├── Procfile                          # Configuración de despliegue PaaS (Render, Railway, Heroku)
├── render.yaml                       # Blueprint de despliegue automatizado en Render.com
├── requirements.txt                  # Dependencias optimizadas para producción
├── .gitignore                        # Reglas estrictas para excluir datos pesados (>100MB) y cachés
├── README.md                         # Documentación institucional y guía de uso
├── INFORME_SISTEMA_SIPI_INCENDIOS.md # Informe técnico de ingeniería del sistema completo
├── INFORME_MINIPROYECTO.md           # Informe de ciencia de datos, EDA y preguntas de negocio
├── Miniproyecto_SIpi_Incendios.ipynb # Notebook interactivo del análisis exploratorio (EDA)
├── src/
│   ├── config.py                     # Configuración central de rutas relativas y constantes
│   ├── data/                         # Pipeline de extracción y cruce geoespacial
│   │   ├── merge_itrend.py           # Unificación de datos históricos de CONAF/Itrend
│   │   ├── fetch_weather.py          # Extractor modular de clima vía Open-Meteo
│   │   ├── create_dataset.py         # Generación de dataset con muestras y clima
│   │   ├── download_mapbiomas.py     # Descarga automatizada de coberturas MapBiomas
│   │   ├── add_spatial_features.py   # Cruce espacial con capas GeoTIFF
│   │   ├── add_anthropogenic.py      # Distancia a poblados (BallTree de GeoNames)
│   │   ├── add_topography.py         # Elevación, pendiente y aspecto (NASA SRTM)
│   │   └── process_viirs.py          # Procesamiento satelital VIIRS
│   ├── models/                       # Modelos serializados y entrenamiento
│   │   ├── train_model_final.py      # Entrenamiento XGBoost V2 + Optuna + Sample Weights
│   │   ├── xgboost_fire_model_final.pkl # Modelo entrenado en producción (1.66 MB)
│   │   └── model_metadata_final.pkl  # Metadatos, métricas y features
│   ├── evaluation/                   # Diagnóstico y explicabilidad
│   │   ├── evaluate_model.py         # Generación de métricas y gráficos
│   │   ├── evaluation_report.json    # Métricas estructuradas para el dashboard
│   │   └── *.png                     # Curvas PR, ROC, calibración, error y SHAP
│   └── dashboard/                    # Visualizador Web Interactivo (Flask + Vanilla SPA)
│       ├── server.py                 # Backend Flask (Inferencia, SHAP, Forecast, Simulador)
│       └── static/                   # Frontend SPA Glassmorphism
│           ├── index.html            # Dashboard modular con 4 pestañas interactivas
│           ├── css/styles.css        # Sistema de diseño moderno con Leaflet oscuro
│           └── js/app.js             # Lógica cliente, tacómetro dinámico y gráficos
├── data/
│   ├── raw/                          # Insumos esenciales (GeoNames CL.txt para poblados)
│   └── processed/                    # Muestra georreferenciada de focos históricos
└── tests/                            # Suite completa de pruebas unitarias (17 tests)
    ├── test_features.py              # Pruebas de features e índices climáticos
    ├── test_model.py                 # Pruebas de inferencia y explicabilidad SHAP
    └── test_server.py                # Pruebas de integración de la API Flask
```

---

## 📊 Variables del Modelo (22 Features)

| Categoría | Variable | Descripción | Fuente |
|---|---|---|---|
| **Clima (Ventana 7d)** | `temp_max_window` | Temperatura máxima en la ventana | Open-Meteo API |
| | `temp_mean_window` | Temperatura promedio en la ventana | Open-Meteo API |
| | `humidity_min_window`| Humedad relativa mínima (%) | Open-Meteo API |
| | `humidity_mean_window`| Humedad relativa promedio (%) | Open-Meteo API |
| | `precip_acc_window` | Precipitación acumulada (mm) | Open-Meteo API |
| | `wind_speed_max_window`| Velocidad máxima del viento (km/h) | Open-Meteo API |
| | `wind_speed_mean_window`| Velocidad media del viento (km/h) | Open-Meteo API |
| | `soil_temp_mean` | Temperatura media del suelo (0-7 cm) | Open-Meteo API |
| | `soil_moisture_mean` | Humedad volumétrica del suelo (0-7 cm) | Open-Meteo API |
| **Vegetación** | `land_cover_class` | Clase de cobertura de suelo (Pino, Eucalipto, Bosque Nativo, etc.) | MapBiomas Chile 2022 |
| **Antrópico** | `dist_nearest_town_km`| Distancia esférica al poblado más cercano (km) | GeoNames (BallTree) |
| **Topografía** | `elevation` | Elevación sobre el nivel del mar (m) | NASA SRTM |
| | `slope_deg` | Pendiente topográfica del terreno (grados) | NASA SRTM |
| | `aspect_deg` | Orientación de ladera (0°=N, 90°=E, 180°=S, 270°=W)| NASA SRTM |
| **Temporal** | `month_sin`, `month_cos`| Encoding cíclico senoidal/cosenoidal del mes | Fecha del registro |
| | `day_of_year` | Día del año (1–366) | Fecha del registro |
| | `season` | Estación del año en el hemisferio sur (1=Verano a 4=Primavera)| Fecha del registro |
| **Interacción** | `dryness_index` | Índice de sequedad `Temp_max * (100 - Hum_mean) / 100` | Derivada |
| | `precip_drought` | Indicador binario de sequía (`precip_acc < 1.0 mm`) | Derivada |
| | `temp_humidity_ratio`| Ratio de evaporación extrema `Temp_max / (Hum_min + 1)` | Derivada |
| | `fire_weather_index` | Índice Meteorológico de Fuego `(Temp_max * Viento_max) / (Hum_min + 1)`| Derivada |

---

## 🎯 Validación Temporal y Rendimiento

El modelo se entrena bajo una estricta estrategia de **Split Temporal** para garantizar ausencia total de data leakage (*fuga de información futura*):

- **Conjunto de Entrenamiento:** Registros de 2002 a 2018 (5.848 muestras)
- **Conjunto de Evaluación:** Registros de 2019 a 2020 (968 muestras nunca vistas durante el tuning)

### Métricas de Evaluación
- **ROC-AUC:** `0.7932`
- **F1-Score:** `0.7515`
- **Average Precision (PR-AUC):** `0.7975`
- **Recall de Incendios:** `88.84%`
- **Accuracy Global:** `69.52%`
- **Brier Score (Calibración Probabilística):** `0.2221`

---

## 🚀 Ejecución Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/Paimilla/Sipi_incendios.git
cd Sipi_incendios
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Ejecutar la suite de pruebas automatizadas
```bash
python -m pytest tests/ -v
```

### 4. Iniciar el visualizador web
```bash
python app.py
```
Abre en tu navegador: **`http://localhost:5000`**

---

## 🌐 Módulos del Dashboard Interactivo

1. **📍 Predicción Puntual y Mapa Geoespacial:**
   - Mapa interactivo Leaflet con capas Oscura, Satelital y Calles.
   - Capa conmutable de **focos históricos de incendios de CONAF/Itrend**.
   - Tacómetro dinámico con niveles de riesgo: **Bajo**, **Moderado**, **Alto** y **Crítico**.
   - Tarjetas de entorno geoespacial real (Uso de suelo MapBiomas, Poblado más cercano, Elevación, Pendiente).
   - **Explicador SHAP en vivo** con desglose de variables que aumentan o disminuyen el riesgo.

2. **📅 Pronóstico de Riesgo a 7 Días:**
   - Consulta el pronóstico meteorológico horario de Open-Meteo y calcula la curva de riesgo proyectada para la próxima semana en el punto seleccionado.

3. **🧪 Simulador Climático "¿Qué pasaría si...?":**
   - Sliders interactivos para variar Temperatura, Humedad, Viento, Pendiente y Cobertura Vegetal.
   - Botones de escenarios rápidos (*Ola de calor extrema*, *Viento Puelche*, *Frente lluvioso*, *Restauración ecológica*).
   - Comparativa inmediata entre condición base y simulada con cálculo de deltas y SHAP.

4. **📊 Diagnóstico y Métricas del Modelo:**
   - Tablero de métricas del modelo y galería con 10 gráficos diagnósticos en alta definición con visualizador modal Lightbox.

---

## 🔌 API Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Interfaz gráfica del Dashboard |
| `POST` | `/api/predict` | Predicción puntual de riesgo con inferencia espacial y SHAP |
| `POST` | `/api/forecast` | Pronóstico de riesgo a 7 días en coordenadas dadas |
| `POST` | `/api/simulate` | Simulación de escenarios climáticos What-If y deltas |
| `GET` | `/api/historical-hotspots` | Muestra georreferenciada de focos históricos de incendios |
| `GET` | `/api/model-info` | Metadatos de entrenamiento, versión y métricas del modelo |
| `GET` | `/api/evaluation-plots` | Listado de gráficos de evaluación disponibles |
| `GET` | `/api/plot/<filename>` | Servidor de imágenes de evaluación |

---

## 🔒 Seguridad y Privacidad

- **Cero Tokens / Secretos:** El proyecto utiliza exclusivamente APIs públicas y abiertas (Open-Meteo y NASA SRTM), por lo que no requiere almacenar tokens privados, API keys ni credenciales en el código.
- **Rutas Relativas:** Todas las rutas del proyecto son relativas y portables, garantizando compatibilidad en Windows, Linux y entornos contenerizados en la nube.
- **Optimización de Almacenamiento:** El repositorio excluye automáticamente archivos binarios masivos (>100MB) para cumplir estrictamente con los límites de GitHub.

---

## 📚 Fuentes de Datos y Créditos

- **CONAF / Itrend:** Base de datos histórica de incendios forestales de Chile (1985–2023).
- **Open-Meteo:** API Meteorológica global histórica y de pronóstico horario.
- **MapBiomas Chile:** Colección 1 (2022) de cobertura y uso de suelo a resolución de 30m.
- **GeoNames:** Base de datos geográfica de asentamientos humanos de Chile.
- **NASA SRTM:** Shuttle Radar Topography Mission (Modelo Digital de Elevación).

---
*SIpi Incendios — Sistema Inteligente de Predicción de Incendios Forestales (Chile)*
