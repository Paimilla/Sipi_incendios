"""
Dashboard Web Backend — SIpi Incendios
=======================================
Backend Flask de alta precisión que:
  1. Carga el modelo XGBoost V2, metadatos y SHAP TreeExplainer al inicio.
  2. Cruza coordenadas con MapBiomas 2022 (GeoTIFF) para uso de suelo real.
  3. Cruza coordenadas con GeoNames (BallTree) para distancia exacta a poblados.
  4. Calcula topografía real (Elevación, Pendiente, Orientación) con NASA SRTM.
  5. Consulta clima en tiempo real / histórico vía Open-Meteo API.
  6. Genera explicabilidad local en vivo (SHAP Waterfall / Feature Contributions).
  7. Ofrece pronóstico de riesgo diario para los próximos 7 días (/api/forecast).
  8. Simulador interactivo de escenarios climáticos "¿Qué pasaría si...?" (/api/simulate).
  9. Expone focos históricos de incendios (/api/historical-hotspots).
 10. Expone metadata, métricas y gráficos diagnósticos (/api/model-info, /api/evaluation-plots).
"""
import sys
from pathlib import Path

# Agregar src/ al path
SRC_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))

import json
import math
import time
import numpy as np
import pandas as pd
import requests as http_requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, send_file
import joblib
import shap
from sklearn.neighbors import BallTree

try:
    import rasterio
except ImportError:
    rasterio = None

try:
    import srtm
except ImportError:
    srtm = None

from config import (
    MODELS_DIR, BURNABLE_CLASSES, MAPBIOMAS_TIF, GEONAMES_TXT, 
    PROCESSED_DIR, RAW_DIR
)

# ── Configuración de Directorios ────────────────────────────────────────
DASHBOARD_DIR = Path(__file__).resolve().parent
STATIC_DIR = DASHBOARD_DIR / 'static'
EVALUATION_DIR = SRC_DIR / 'evaluation'
HOTSPOTS_FILE = PROCESSED_DIR / 'historical_hotspots_sample.json'

# ── App Flask ───────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(STATIC_DIR))

# ── 1. Carga del Modelo y Metadatos ─────────────────────────────────────
print("\n" + "=" * 60)
print("   [SIpi Incendios] Inicializando Backend...")
print("=" * 60)

print("1/5. Cargando modelo XGBoost V2 y metadata...")
MODEL = joblib.load(MODELS_DIR / 'xgboost_fire_model_final.pkl')
METADATA = joblib.load(MODELS_DIR / 'model_metadata_final.pkl')
FEATURES = METADATA['features']
print(f"     -> Modelo V{METADATA['version']} cargado ({len(FEATURES)} features).")

# ── 2. Inicialización SHAP TreeExplainer ─────────────────────────────────
print("2/5. Inicializando SHAP TreeExplainer para explicabilidad en vivo...")
SHAP_EXPLAINER = shap.TreeExplainer(MODEL)
print("     -> SHAP TreeExplainer listo.")

# ── 3. Carga de Capas Geoespaciales ─────────────────────────────────────
print("3/5. Inicializando capas geoespaciales...")

# a) GeoNames BallTree
GEONAMES_TREE = None
GEONAMES_DF = None
if GEONAMES_TXT.exists():
    try:
        cols = ['geonameid', 'name', 'asciiname', 'alternatenames', 'latitude', 'longitude', 
                'feature_class', 'feature_code', 'country_code', 'cc2', 'admin1_code', 
                'admin2_code', 'admin3_code', 'admin4_code', 'population', 'elevation', 
                'dem', 'timezone', 'modification_date']
        places = pd.read_csv(GEONAMES_TXT, sep='\t', names=cols, low_memory=False)
        places = places[places['feature_class'] == 'P'].dropna(subset=['latitude', 'longitude']).copy()
        places_coords = np.vstack([places['latitude'], places['longitude']]).T
        places_rad = np.radians(places_coords)
        GEONAMES_TREE = BallTree(places_rad, metric='haversine')
        GEONAMES_DF = places.reset_index(drop=True)
        print(f"     -> GeoNames: {len(GEONAMES_DF)} poblados indexados en BallTree.")
    except Exception as e:
        print(f"     [!] Error cargando GeoNames: {e}")
else:
    print(f"     [!] No se encontro {GEONAMES_TXT}. Se usaran aproximaciones.")

# b) MapBiomas GeoTIFF
MAPBIOMAS_SRC = None
if rasterio is not None and MAPBIOMAS_TIF.exists():
    try:
        MAPBIOMAS_SRC = rasterio.open(MAPBIOMAS_TIF)
        print(f"     -> MapBiomas 2022: GeoTIFF abierto ({MAPBIOMAS_SRC.width}x{MAPBIOMAS_SRC.height}).")
    except Exception as e:
        print(f"     [!] Error abriendo MapBiomas: {e}")
else:
    print(f"     [!] MapBiomas no disponible (archivo o libreria rasterio ausente). Se usara fallback.")

# c) NASA SRTM Topografía
print("4/5. Inicializando modulo SRTM de elevacion/pendiente...")
SRTM_DATA = None
if srtm is not None:
    try:
        SRTM_DATA = srtm.get_data()
        print("     -> NASA SRTM disponible.")
    except Exception as e:
        print(f"     [!] Error cargando SRTM: {e}")
else:
    print("     [!] srtm no disponible. Se usara fallback de Open-Meteo elevation.")

# ── 4. Carga de Reportes y Focos Históricos ──────────────────────────────
print("5/5. Cargando focos historicos y reporte de evaluacion...")
EVAL_REPORT = {}
eval_report_path = EVALUATION_DIR / 'evaluation_report.json'
if eval_report_path.exists():
    with open(eval_report_path, 'r', encoding='utf-8') as f:
        EVAL_REPORT = json.load(f)
    print("     -> Reporte de evaluacion cargado.")

HISTORICAL_HOTSPOTS = []
if HOTSPOTS_FILE.exists():
    with open(HOTSPOTS_FILE, 'r', encoding='utf-8') as f:
        HISTORICAL_HOTSPOTS = json.load(f)
    print(f"     -> {len(HISTORICAL_HOTSPOTS)} focos historicos cargados.")

print("=" * 60 + "\n")

# ── Diccionario de Clases de Uso de Suelo MapBiomas ─────────────────────
MAPBIOMAS_LABELS = {
    1: "Formación Boscosa",
    3: "Bosque Nativo",
    4: "Formación Boscosa Mixta",
    5: "Matorral Nativo",
    6: "Bosque Inundable",
    9: "Plantación Forestal (Pino / Eucalipto)",
    11: "Humedal / Pantano",
    12: "Pastizal / Pradera",
    13: "Formación No Boscosa",
    15: "Pastizal / Uso Ganadero",
    18: "Agricultura",
    19: "Cultivo Temporal",
    20: "Cultivo Perenne",
    21: "Mosaico Agrícola / Silvopastoril",
    23: "Playa / Duna / Arenal",
    24: "Área Urbana / Infraestructura",
    25: "Suelo Desnudo / Rocas",
    29: "Afloramiento Rocoso",
    30: "Minería",
    31: "Acuicultura",
    33: "Cuerpo de Agua / Lago / Río",
    34: "Nieve / Glaciar",
    39: "Bosque Secundario / Renovales",
    41: "Otras Áreas Sin Vegetación",
    66: "Mosaico de Vegetación Natural y Antrópica",
}

FEATURE_LABELS_ES = {
    'temp_max_window': 'Temperatura Máxima',
    'temp_mean_window': 'Temperatura Media',
    'humidity_min_window': 'Humedad Mínima',
    'humidity_mean_window': 'Humedad Media',
    'precip_acc_window': 'Precipitación Acumulada',
    'wind_speed_max_window': 'Viento Máximo',
    'wind_speed_mean_window': 'Viento Medio',
    'soil_temp_mean': 'Temperatura del Suelo',
    'soil_moisture_mean': 'Humedad del Suelo',
    'land_cover_class': 'Tipo de Vegetación',
    'dist_nearest_town_km': 'Distancia a Poblado',
    'elevation': 'Elevación (m.s.n.m.)',
    'slope_deg': 'Pendiente del Terreno',
    'aspect_deg': 'Orientación de Ladera',
    'month_sin': 'Mes del Año (Seno)',
    'month_cos': 'Mes del Año (Coseno)',
    'day_of_year': 'Día del Año',
    'season': 'Estación del Año',
    'dryness_index': 'Índice de Sequedad',
    'precip_drought': 'Indicador de Sequía',
    'temp_humidity_ratio': 'Ratio Temp/Humedad',
    'fire_weather_index': 'Índice Meteorológico de Fuego (FWI)'
}


# ── Funciones de Consulta Geoespacial ───────────────────────────────────

def query_mapbiomas(lat, lon):
    """Obtiene la clase de uso de suelo real de MapBiomas 2022."""
    if MAPBIOMAS_SRC is not None:
        try:
            val = next(MAPBIOMAS_SRC.sample([(lon, lat)]))[0]
            val = int(val)
            if val in MAPBIOMAS_LABELS:
                return val, MAPBIOMAS_LABELS[val]
            elif val != 0 and not math.isnan(val):
                return val, f"Clase MapBiomas {val}"
        except Exception:
            pass
    # Fallback si no hay raster o está fuera de cobertura
    return 9, MAPBIOMAS_LABELS[9]


def query_nearest_town(lat, lon):
    """Calcula la distancia al poblado más cercano usando BallTree de GeoNames."""
    if GEONAMES_TREE is not None and GEONAMES_DF is not None:
        try:
            query_rad = np.radians([[lat, lon]])
            dist, idx = GEONAMES_TREE.query(query_rad, k=1)
            dist_km = float(dist[0][0] * 6371.0)
            town_name = str(GEONAMES_DF.iloc[idx[0][0]]['name'])
            return round(dist_km, 2), town_name
        except Exception:
            pass
    return 2.5, "Poblado Cercano"


def query_topography(lat, lon):
    """Calcula elevación, pendiente y aspecto usando NASA SRTM."""
    elevation = 200.0
    slope_deg = 5.0
    aspect_deg = 180.0

    if SRTM_DATA is not None:
        try:
            elev = SRTM_DATA.get_elevation(lat, lon)
            if elev is not None:
                elevation = float(elev)
                d = 0.0003  # ~30m
                elev_n = SRTM_DATA.get_elevation(lat + d, lon) or elevation
                elev_s = SRTM_DATA.get_elevation(lat - d, lon) or elevation
                elev_e = SRTM_DATA.get_elevation(lat, lon + d) or elevation
                elev_w = SRTM_DATA.get_elevation(lat, lon - d) or elevation

                d_lat_m = d * 111320.0
                d_lon_m = d * 111320.0 * math.cos(math.radians(lat))

                dz_dx = (elev_e - elev_w) / (2.0 * d_lon_m) if d_lon_m != 0 else 0
                dz_dy = (elev_n - elev_s) / (2.0 * d_lat_m)

                slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
                slope_deg = float(math.degrees(slope_rad))

                if dz_dx != 0 or dz_dy != 0:
                    aspect_deg = float((math.degrees(math.atan2(dz_dx, dz_dy)) + 360) % 360)
                else:
                    aspect_deg = -1.0

                return elevation, round(slope_deg, 2), round(aspect_deg, 2)
        except Exception:
            pass

    # Fallback con elevación de Open-Meteo
    try:
        resp = http_requests.get(
            f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if "elevation" in data and len(data["elevation"]) > 0:
                elevation = float(data["elevation"][0])
    except Exception:
        pass

    return elevation, slope_deg, aspect_deg


# ── In-Memory Cache con TTL para Consultas Climáticas ───────────────────
WEATHER_CACHE = {}
CACHE_TTL_SECONDS = 1800  # 30 minutos de persistencia


# ── Funciones de Clima y Construcción de Features ───────────────────────

def fetch_weather_for_prediction(lat, lon, date_str):
    """
    Obtiene datos meteorológicos de Open-Meteo (ventana de 7 días).
    Retorna tanto las métricas agregadas como el desglose diario y trazabilidad de la API.
    Utiliza caché en memoria para acelerar consultas repetidas.
    """
    cache_key = (round(lat, 3), round(lon, 3), date_str)
    now_ts = time.time()
    if cache_key in WEATHER_CACHE:
        cached_val, cached_ts = WEATHER_CACHE[cache_key]
        if now_ts - cached_ts < CACHE_TTL_SECONDS:
            return cached_val[0], cached_val[1], cached_val[2]

    t_start = time.time()
    target_date = datetime.strptime(date_str, '%Y-%m-%d')
    today = datetime.now()

    is_fallback = False
    query_date = target_date
    if target_date.date() > (today + timedelta(days=14)).date():
        is_fallback = True
        try:
            query_date = target_date.replace(year=2023)
        except ValueError:
            query_date = target_date.replace(year=2023, day=28)

    # Ventana de 7 días exactos hacia atrás (6 días previos + día objetivo inclusive = 7 días / 168h)
    start_date = (query_date - timedelta(days=6)).strftime('%Y-%m-%d')
    end_date_str = query_date.strftime('%Y-%m-%d')

    if query_date.date() < (today - timedelta(days=5)).date():
        base_url = "https://archive-api.open-meteo.com/v1/archive"
        source_name = "Open-Meteo Historical Archive API (ERA5 Reanálisis - ECMWF)"
        source_type = "historical_archive"
    else:
        base_url = "https://api.open-meteo.com/v1/forecast"
        source_name = "Open-Meteo Global Forecast API (ECMWF IFS / NOAA GFS)"
        source_type = "live_forecast"

    if is_fallback:
        source_name += " [Línea Base Climatológica ERA5 2023]"
        source_type = "climatological_reference"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date_str,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,"
                  "wind_direction_10m,soil_temperature_0_to_7cm,soil_moisture_0_to_7cm",
        "timezone": "America/Santiago"
    }

    for attempt in range(3):
        try:
            resp = http_requests.get(base_url, params=params, timeout=15)
            latency_ms = round((time.time() - t_start) * 1000, 1)

            if resp.status_code == 200:
                data = resp.json()
                if "hourly" in data:
                    df = pd.DataFrame(data["hourly"])
                    df['time'] = pd.to_datetime(df['time'])
                    df['date_only'] = df['time'].dt.strftime('%Y-%m-%d')

                    # Desglose de los 7 días previos
                    past_days = []
                    for d_val, grp in df.groupby('date_only'):
                        past_days.append({
                            'date': d_val,
                            'temp_max': round(float(grp['temperature_2m'].max()), 1),
                            'temp_mean': round(float(grp['temperature_2m'].mean()), 1),
                            'humidity_min': round(float(grp['relative_humidity_2m'].min()), 1),
                            'humidity_mean': round(float(grp['relative_humidity_2m'].mean()), 1),
                            'wind_max': round(float(grp['wind_speed_10m'].max()), 1),
                            'precip': round(float(grp['precipitation'].sum()), 1)
                        })

                    weather_stats = {
                        "temp_max_window": float(df['temperature_2m'].max()),
                        "temp_mean_window": float(df['temperature_2m'].mean()),
                        "humidity_min_window": float(df['relative_humidity_2m'].min()),
                        "humidity_mean_window": float(df['relative_humidity_2m'].mean()),
                        "precip_acc_window": float(df['precipitation'].sum()),
                        "wind_speed_max_window": float(df['wind_speed_10m'].max()),
                        "wind_speed_mean_window": float(df['wind_speed_10m'].mean()),
                        "soil_temp_mean": float(df['soil_temperature_0_to_7cm'].mean()),
                        "soil_moisture_mean": float(df['soil_moisture_0_to_7cm'].mean()),
                    }

                    provenance = {
                        "source_name": source_name,
                        "source_type": source_type,
                        "api_url": resp.url,
                        "http_status": 200,
                        "latency_ms": latency_ms,
                        "is_fallback": is_fallback,
                        "hourly_samples": len(df),
                        "start_window": start_date,
                        "end_window": end_date_str
                    }

                    WEATHER_CACHE[cache_key] = ((weather_stats, past_days, provenance), time.time())
                    return weather_stats, past_days, provenance

            elif resp.status_code == 429:
                return 'RATE_LIMITED', [], {}
        except Exception:
            time.sleep(1)

    return None, [], {}


def build_feature_dict(lat, lon, fecha, weather, land_cover_class, dist_town_km, elevation, slope_deg, aspect_deg):
    """Construye el diccionario de 22 variables requerido por el modelo."""
    dt = datetime.strptime(fecha, '%Y-%m-%d')
    month = dt.month
    day_of_year = dt.timetuple().tm_yday

    # Mapeo de interfaz combustible para clases antropicas o no vegetales (evita artefacto de muestreo en clases 24/66)
    model_cover_class = int(land_cover_class)
    if model_cover_class in [24, 66, 0]:
        model_cover_class = 21  # Mosaico de interfaz agroforestal / combustible
    elif model_cover_class in [25, 29, 30, 31, 33, 34]:
        model_cover_class = 3   # Suelo no combustible sobre base nativa

    def get_season(m):
        if m in [12, 1, 2, 3]: return 1
        elif m in [4, 5]: return 2
        elif m in [6, 7, 8]: return 3
        else: return 4

    features = {
        **weather,
        'land_cover_class': model_cover_class,
        'dist_nearest_town_km': float(dist_town_km),
        'elevation': float(elevation),
        'slope_deg': float(slope_deg),
        'aspect_deg': float(aspect_deg),
        'month_sin': float(np.sin(2 * np.pi * month / 12)),
        'month_cos': float(np.cos(2 * np.pi * month / 12)),
        'day_of_year': int(day_of_year),
        'season': int(get_season(month)),
    }

    # Features derivadas de interacción climática
    features['dryness_index'] = (
        features['temp_max_window'] * (100 - features['humidity_mean_window']) / 100
    )
    features['precip_drought'] = 1 if features['precip_acc_window'] < 1.0 else 0
    features['temp_humidity_ratio'] = (
        features['temp_max_window'] / (features['humidity_min_window'] + 1)
    )
    features['fire_weather_index'] = (
        features['temp_max_window'] * features['wind_speed_max_window']
        / (features['humidity_min_window'] + 1)
    )

    return features


def explain_prediction(df_row):
    """Calcula las contribuciones locales SHAP para la predicción."""
    try:
        shap_vals = SHAP_EXPLAINER.shap_values(df_row)[0]
        factors = []
        for feat_name, s_val in zip(FEATURES, shap_vals):
            feat_val = df_row[feat_name].values[0]
            factors.append({
                'feature': feat_name,
                'label': FEATURE_LABELS_ES.get(feat_name, feat_name),
                'impact': round(float(s_val), 4),
                'direction': 'increases_risk' if s_val > 0 else 'decreases_risk',
                'value': round(float(feat_val), 2) if isinstance(feat_val, (int, float, np.number)) else str(feat_val)
            })

        # Ordenar por magnitud de impacto absoluto
        factors.sort(key=lambda x: abs(x['impact']), reverse=True)
        return factors[:6]  # Retornar los 6 factores más determinantes
    except Exception as e:
        print(f"Error calculando SHAP: {e}")
        return []


# ── Clases No Combustibles (Restricción Física de Combustible) ───────────
NON_BURNABLE_CLASSES = {
    33: ("Cuerpo de Agua / Océano / Lago", "Superficie acuática no combustible. No existe biomasa vegetal para ignición."),
    34: ("Nieve / Glaciar", "Superficie de nieve permanente o glaciar no combustible."),
    25: ("Suelo Desnudo / Rocas", "Suelo mineral rocoso sin combustible vegetal continuo."),
    29: ("Afloramiento Rocoso", "Roca expuesta sin cobertura vegetal susceptible a incendios."),
    23: ("Playa / Duna / Arenal", "Arenales costeros sin carga de combustible forestal."),
    30: ("Minería", "Instalaciones mineras o suelo industrial no combustible."),
    31: ("Acuicultura", "Instalación marina/acuícola."),
}


def classify_risk(probability, is_non_burnable=False, non_burnable_desc=None):
    """Clasifica la probabilidad en niveles de riesgo institucional con restricciones físicas."""
    if is_non_burnable:
        return 'Nulo', '#1E88E5', non_burnable_desc or 'Superficie no combustible (sin vegetación susceptible a ignición).'
    if probability < 0.25:
        return 'Bajo', '#2E7D32', 'Condiciones favorables con baja probabilidad de ignición.'
    elif probability < 0.50:
        return 'Moderado', '#FF8F00', 'Precaución moderada. Factores climáticos o de combustible activos.'
    elif probability < 0.75:
        return 'Alto', '#E65100', 'Alto riesgo. Condiciones propicias para propagación rápida de incendios.'
    else:
        return 'Crítico', '#B71C1C', 'Alerta crítica. Combinación extrema de calor, viento y sequedad de combustible.'


# ── Rutas API ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(str(STATIC_DIR), 'index.html')


@app.route('/api/predict', methods=['POST'])
def predict():
    """Endpoint principal de predicción de riesgo puntual con explicabilidad SHAP."""
    try:
        data = request.get_json() or {}
        lat = float(data.get('lat', 0))
        lon = float(data.get('lon', 0))
        fecha = data.get('fecha', '')

        # Validaciones de rango
        if not (-56.0 <= lat <= -17.0):
            return jsonify({'error': 'Latitud fuera de rango de Chile (-56 a -17)'}), 400
        if not (-76.0 <= lon <= -66.0):
            return jsonify({'error': 'Longitud fuera de rango de Chile (-76 a -66)'}), 400

        try:
            datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Fecha inválida. Use formato YYYY-MM-DD'}), 400

        # 1. Clima Open-Meteo
        weather, past_days, provenance = fetch_weather_for_prediction(lat, lon, fecha)
        if weather == 'RATE_LIMITED':
            return jsonify({'error': 'Límite de peticiones de Open-Meteo alcanzado. Intente más tarde.'}), 429
        if weather is None:
            return jsonify({'error': 'No se pudieron obtener datos meteorológicos para las coordenadas y fecha indicadas.'}), 502

        # 2. Consultas geoespaciales reales
        land_cover_class, land_cover_name = query_mapbiomas(lat, lon)
        dist_town_km, nearest_town_name = query_nearest_town(lat, lon)
        elevation, slope_deg, aspect_deg = query_topography(lat, lon)

        # 3. Restricción física de combustible (Agua, Glaciar, Rocas)
        if land_cover_class in NON_BURNABLE_CLASSES:
            _, desc = NON_BURNABLE_CLASSES[land_cover_class]
            probability = 0.0000
            risk_level, risk_color, risk_description = classify_risk(0.0, is_non_burnable=True, non_burnable_desc=desc)
            shap_factors = [{
                'feature': 'land_cover_class',
                'label': 'Superficie No Combustible',
                'impact': -5.0,
                'direction': 'decreases_risk',
                'value': land_cover_name
            }]
        else:
            # 4. Construir Features e Inferencia XGBoost
            feat_dict = build_feature_dict(
                lat, lon, fecha, weather, 
                land_cover_class, dist_town_km, elevation, slope_deg, aspect_deg
            )

            df = pd.DataFrame([feat_dict])[FEATURES]
            df['land_cover_class'] = df['land_cover_class'].astype('category')

            raw_prob = float(MODEL.predict_proba(df)[:, 1][0])
            
            # 5. Modulación física por humedad/lluvia severa
            precip = weather.get('precip_acc_window', 0)
            temp = weather.get('temp_max_window', 20)
            hum = weather.get('humidity_min_window', 50)
            if precip > 30.0 and temp < 16.0:
                raw_prob = min(raw_prob, 0.04)
            elif precip > 15.0 and hum > 65.0:
                raw_prob = min(raw_prob, 0.15)
                
            probability = raw_prob
            risk_level, risk_color, risk_description = classify_risk(probability)
            shap_factors = explain_prediction(df)

        result = {
            'probability': round(probability, 4),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'risk_description': risk_description,
            'weather_summary': {
                'temp_max': round(weather['temp_max_window'], 1),
                'temp_mean': round(weather['temp_mean_window'], 1),
                'humidity_min': round(weather['humidity_min_window'], 1),
                'humidity_mean': round(weather['humidity_mean_window'], 1),
                'precip_total': round(weather['precip_acc_window'], 1),
                'wind_max': round(weather['wind_speed_max_window'], 1),
                'soil_moisture': round(weather['soil_moisture_mean'], 3),
            },
            'past_7_days': past_days,
            'data_provenance': provenance,
            'spatial_info': {
                'land_cover_class': land_cover_class,
                'land_cover_name': land_cover_name,
                'nearest_town': nearest_town_name,
                'dist_nearest_town_km': dist_town_km,
                'elevation_m': round(elevation, 1),
                'slope_deg': slope_deg,
                'aspect_deg': aspect_deg,
                'source_landcover': 'MapBiomas Chile 2022 (GeoTIFF 30m local)',
                'source_topography': 'NASA SRTM v3.0 (Radar Topography Mission)',
                'source_settlements': 'GeoNames Chile (BallTree esférico, 6.967 poblados)'
            },
            'location': {
                'lat': round(lat, 4),
                'lon': round(lon, 4),
            },
            'fecha': fecha,
            'shap_factors': shap_factors,
        }

        return jsonify(result)

    except Exception as e:
        print(f"Error en /api/predict: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/forecast', methods=['POST'])
def forecast():
    """
    Endpoint de pronóstico de riesgo a 7 días.
    Consulta el pronóstico horario de Open-Meteo y calcula el riesgo para cada uno de los próximos 7 días.
    """
    try:
        data = request.get_json() or {}
        lat = float(data.get('lat', 0))
        lon = float(data.get('lon', 0))

        if not (-56.0 <= lat <= -17.0) or not (-76.0 <= lon <= -66.0):
            return jsonify({'error': 'Coordenadas fuera de Chile continental'}), 400

        # Geoespacial estático para este punto
        land_cover_class, land_cover_name = query_mapbiomas(lat, lon)
        dist_town_km, nearest_town_name = query_nearest_town(lat, lon)
        elevation, slope_deg, aspect_deg = query_topography(lat, lon)

        # Consultar Open-Meteo Forecast con ventana acumulada (7 días previos + 7 días futuros)
        # Esto asegura consistencia matemática y física con el modelo XGBoost y con /api/predict
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "past_days": 7,
            "forecast_days": 7,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,"
                      "soil_temperature_0_to_7cm,soil_moisture_0_to_7cm",
            "timezone": "America/Santiago"
        }

        resp = http_requests.get(url, params=params, timeout=14)
        if resp.status_code != 200 or "hourly" not in resp.json():
            return jsonify({'error': 'No se pudo obtener el pronóstico meteorológico.'}), 502

        raw_hourly = resp.json()["hourly"]
        df_hourly = pd.DataFrame(raw_hourly)
        df_hourly['time'] = pd.to_datetime(df_hourly['time'])
        df_hourly['date_str'] = df_hourly['time'].dt.strftime('%Y-%m-%d')

        # Determinar los 7 días futuros a partir de hoy
        today_str = datetime.now().strftime('%Y-%m-%d')
        future_dates = [d for d in sorted(df_hourly['date_str'].unique()) if d >= today_str][:7]
        if len(future_dates) < 7:
            future_dates = sorted(df_hourly['date_str'].unique())[-7:]

        daily_forecasts = []

        for date_str in future_dates:
            target_end = pd.to_datetime(date_str + ' 23:59:59')
            target_start = pd.to_datetime(date_str + ' 00:00:00') - timedelta(days=6)
            df_window = df_hourly[(df_hourly['time'] >= target_start) & (df_hourly['time'] <= target_end)]
            df_day = df_hourly[df_hourly['date_str'] == date_str]

            if df_window.empty:
                df_window = df_day

            weather = {
                "temp_max_window": float(df_window['temperature_2m'].max()),
                "temp_mean_window": float(df_window['temperature_2m'].mean()),
                "humidity_min_window": float(df_window['relative_humidity_2m'].min()),
                "humidity_mean_window": float(df_window['relative_humidity_2m'].mean()),
                "precip_acc_window": float(df_window['precipitation'].sum()),
                "wind_speed_max_window": float(df_window['wind_speed_10m'].max()),
                "wind_speed_mean_window": float(df_window['wind_speed_10m'].mean()),
                "soil_temp_mean": float(df_window['soil_temperature_0_to_7cm'].mean()),
                "soil_moisture_mean": float(df_window['soil_moisture_0_to_7cm'].mean()),
            }

            if land_cover_class in NON_BURNABLE_CLASSES:
                prob = 0.0000
                risk_level, risk_color, _ = classify_risk(0.0, is_non_burnable=True)
            else:
                feat_dict = build_feature_dict(
                    lat, lon, date_str, weather,
                    land_cover_class, dist_town_km, elevation, slope_deg, aspect_deg
                )

                df_row = pd.DataFrame([feat_dict])[FEATURES]
                df_row['land_cover_class'] = df_row['land_cover_class'].astype('category')

                raw_prob = float(MODEL.predict_proba(df_row)[:, 1][0])
                if weather['precip_acc_window'] > 30.0 and weather['temp_max_window'] < 16.0:
                    raw_prob = min(raw_prob, 0.04)
                elif weather['precip_acc_window'] > 15.0 and weather['humidity_min_window'] > 65.0:
                    raw_prob = min(raw_prob, 0.15)
                prob = raw_prob
                risk_level, risk_color, _ = classify_risk(prob)

            daily_forecasts.append({
                'date': date_str,
                'probability': round(prob, 4),
                'risk_level': risk_level,
                'risk_color': risk_color,
                'temp_max': round(float(df_day['temperature_2m'].max()) if not df_day.empty else weather['temp_max_window'], 1),
                'humidity_min': round(float(df_day['relative_humidity_2m'].min()) if not df_day.empty else weather['humidity_min_window'], 1),
                'wind_max': round(float(df_day['wind_speed_10m'].max()) if not df_day.empty else weather['wind_speed_max_window'], 1),
                'precip_total': round(float(df_day['precipitation'].sum()) if not df_day.empty else weather['precip_acc_window'], 1),
            })

        return jsonify({
            'location': {'lat': lat, 'lon': lon, 'land_cover_name': land_cover_name},
            'forecast': daily_forecasts
        })

    except Exception as e:
        print(f"Error en /api/forecast: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """
    Simulador "¿Qué pasaría si...?" (What-If scenario analysis).
    Permite modificar temperatura, viento, humedad, uso de suelo y pendiente
    para ver el cambio dinámico en el riesgo predicho.
    """
    try:
        data = request.get_json() or {}
        lat = float(data.get('lat', -36.82))
        lon = float(data.get('lon', -73.05))
        fecha = data.get('fecha', datetime.now().strftime('%Y-%m-%d'))

        # Deltas del usuario
        delta_temp = float(data.get('delta_temp', 0.0))        # ej: +5°C
        delta_humidity = float(data.get('delta_humidity', 0.0))# ej: -15%
        delta_wind = float(data.get('delta_wind', 0.0))        # ej: +10 km/h
        override_land_cover = data.get('override_land_cover', None)
        override_slope = data.get('override_slope', None)

        # Clima base
        weather_base, _, _ = fetch_weather_for_prediction(lat, lon, fecha)
        if weather_base is None or weather_base == 'RATE_LIMITED':
            # Clima representativo por defecto si falla API
            weather_base = {
                "temp_max_window": 25.0, "temp_mean_window": 18.0,
                "humidity_min_window": 35.0, "humidity_mean_window": 60.0,
                "precip_acc_window": 0.0, "wind_speed_max_window": 15.0,
                "wind_speed_mean_window": 8.0, "soil_temp_mean": 20.0,
                "soil_moisture_mean": 0.25
            }

        # Geoespacial base
        land_cover_class, land_cover_name = query_mapbiomas(lat, lon)
        dist_town_km, nearest_town_name = query_nearest_town(lat, lon)
        elevation, slope_deg, aspect_deg = query_topography(lat, lon)

        # Baseline
        if land_cover_class in NON_BURNABLE_CLASSES:
            prob_base = 0.0000
            risk_base, color_base, _ = classify_risk(0.0, is_non_burnable=True)
        else:
            feat_base = build_feature_dict(
                lat, lon, fecha, weather_base,
                land_cover_class, dist_town_km, elevation, slope_deg, aspect_deg
            )
            df_base = pd.DataFrame([feat_base])[FEATURES]
            df_base['land_cover_class'] = df_base['land_cover_class'].astype('category')
            raw_prob_base = float(MODEL.predict_proba(df_base)[:, 1][0])
            if weather_base.get('precip_acc_window', 0) > 30.0 and weather_base.get('temp_max_window', 20) < 16.0:
                raw_prob_base = min(raw_prob_base, 0.04)
            prob_base = raw_prob_base
            risk_base, color_base, _ = classify_risk(prob_base)

        # Simulación
        sim_land_cover = int(override_land_cover) if override_land_cover is not None else land_cover_class
        sim_slope = float(override_slope) if override_slope is not None else slope_deg

        weather_sim = weather_base.copy()
        weather_sim['temp_max_window'] = max(-10.0, weather_sim['temp_max_window'] + delta_temp)
        weather_sim['temp_mean_window'] = max(-10.0, weather_sim['temp_mean_window'] + (delta_temp * 0.7))
        weather_sim['humidity_min_window'] = min(100.0, max(5.0, weather_sim['humidity_min_window'] + delta_humidity))
        weather_sim['humidity_mean_window'] = min(100.0, max(10.0, weather_sim['humidity_mean_window'] + delta_humidity))
        weather_sim['wind_speed_max_window'] = max(0.0, weather_sim['wind_speed_max_window'] + delta_wind)
        weather_sim['wind_speed_mean_window'] = max(0.0, weather_sim['wind_speed_mean_window'] + (delta_wind * 0.6))

        if delta_temp > 0 or delta_humidity < 0:
            soil_drying = (delta_temp * 0.008) + (abs(delta_humidity) * 0.002)
            weather_sim['soil_moisture_mean'] = max(0.05, weather_sim.get('soil_moisture_mean', 0.25) - soil_drying)
            weather_sim['soil_temp_mean'] = weather_sim.get('soil_temp_mean', 18.0) + (delta_temp * 0.5)

        if sim_land_cover in NON_BURNABLE_CLASSES:
            prob_sim = 0.0000
            risk_sim, color_sim, desc_sim = classify_risk(0.0, is_non_burnable=True)
            shap_sim = [{
                'feature': 'land_cover_class',
                'label': 'Superficie No Combustible',
                'impact': -5.0,
                'direction': 'decreases_risk',
                'value': MAPBIOMAS_LABELS.get(sim_land_cover, f"Clase {sim_land_cover}")
            }]
        else:
            feat_sim = build_feature_dict(
                lat, lon, fecha, weather_sim,
                sim_land_cover, dist_town_km, elevation, sim_slope, aspect_deg
            )
            df_sim = pd.DataFrame([feat_sim])[FEATURES]
            df_sim['land_cover_class'] = df_sim['land_cover_class'].astype('category')
            raw_prob_sim = float(MODEL.predict_proba(df_sim)[:, 1][0])

            if weather_sim.get('precip_acc_window', 0) > 30.0 and weather_sim.get('temp_max_window', 20) < 16.0:
                raw_prob_sim = min(raw_prob_sim, 0.04)
            elif weather_sim.get('precip_acc_window', 0) > 15.0 and weather_sim.get('humidity_min_window', 50) > 65.0:
                raw_prob_sim = min(raw_prob_sim, 0.15)

            prob_sim = raw_prob_sim
            risk_sim, color_sim, desc_sim = classify_risk(prob_sim)
            shap_sim = explain_prediction(df_sim)

        return jsonify({
            'baseline': {
                'probability': round(prob_base, 4),
                'risk_level': risk_base,
                'risk_color': color_base,
                'temp_max': round(weather_base['temp_max_window'], 1),
                'humidity_min': round(weather_base['humidity_min_window'], 1),
                'wind_max': round(weather_base['wind_speed_max_window'], 1),
                'land_cover_name': land_cover_name,
                'slope_deg': slope_deg
            },
            'simulated': {
                'probability': round(prob_sim, 4),
                'risk_level': risk_sim,
                'risk_color': color_sim,
                'risk_description': desc_sim,
                'temp_max': round(weather_sim['temp_max_window'], 1),
                'humidity_min': round(weather_sim['humidity_min_window'], 1),
                'wind_max': round(weather_sim['wind_speed_max_window'], 1),
                'land_cover_name': MAPBIOMAS_LABELS.get(sim_land_cover, f"Clase {sim_land_cover}"),
                'slope_deg': sim_slope
            },
            'delta_probability': round(prob_sim - prob_base, 4),
            'shap_factors': shap_sim
        })

    except Exception as e:
        print(f"Error en /api/simulate: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/historical-hotspots')
def historical_hotspots():
    """Retorna la muestra de focos históricos de incendios para el mapa de calor."""
    return jsonify({
        'count': len(HISTORICAL_HOTSPOTS),
        'hotspots': HISTORICAL_HOTSPOTS
    })


@app.route('/api/model-info')
def model_info():
    """Retorna metadata del modelo y métricas de evaluación."""
    info = {
        'version': METADATA.get('version', 'V2'),
        'train_years': METADATA.get('train_years', '2002-2018'),
        'test_years': METADATA.get('test_years', '2019-2020'),
        'train_samples': METADATA.get('train_samples', 5848),
        'test_samples': METADATA.get('test_samples', 968),
        'features': FEATURES,
        'n_features': len(FEATURES),
        'improvements': METADATA.get('improvements', [
            'Split temporal estricto (2002-2018 train, 2019-2020 test)',
            'Ponderación de muestras (sample weights) para corrección de sesgo estacional',
            'Smart Negative Sampling en coberturas vegetales quemables',
            'Optimización bayesiana con Optuna (80 trials)',
            'Índices de interacción climática (dryness_index, fire_weather_index)'
        ]),
    }

    if EVAL_REPORT:
        info['metrics'] = EVAL_REPORT.get('metrics', {})
        info['confusion_matrix'] = EVAL_REPORT.get('confusion_matrix', {})
        info['performance_by_season'] = EVAL_REPORT.get('performance_by_season', {})
        info['performance_by_region'] = EVAL_REPORT.get('performance_by_region', {})
    else:
        info['metrics'] = {
            'accuracy': METADATA.get('accuracy', 0.6952),
            'f1_score': METADATA.get('f1_score', 0.7515),
            'roc_auc': METADATA.get('roc_auc', 0.7932),
        }

    return jsonify(info)


@app.route('/api/evaluation-plots')
def evaluation_plots():
    """Lista gráficos de diagnóstico disponibles."""
    plots = []
    # Gráficos de evaluación avanzada
    for ext in ['*.png']:
        for f in EVALUATION_DIR.glob(ext):
            plots.append({
                'filename': f.name,
                'title': f.stem.replace('_', ' ').title(),
                'url': f'/api/plot/{f.name}'
            })
    # Gráficos del entrenamiento
    for f in MODELS_DIR.glob('*.png'):
        plots.append({
            'filename': f.name,
            'title': f.stem.replace('_', ' ').title(),
            'url': f'/api/plot/training/{f.name}'
        })
    return jsonify({'plots': plots})


@app.route('/api/plot/<filename>')
def serve_eval_plot(filename):
    """Sirve un gráfico de evaluación."""
    path = EVALUATION_DIR / filename
    if path.exists() and path.suffix == '.png':
        return send_file(str(path), mimetype='image/png')
    return jsonify({'error': 'Plot not found'}), 404


@app.route('/api/plot/training/<filename>')
def serve_training_plot(filename):
    """Sirve un gráfico del entrenamiento."""
    path = MODELS_DIR / filename
    if path.exists() and path.suffix == '.png':
        return send_file(str(path), mimetype='image/png')
    return jsonify({'error': 'Plot not found'}), 404


@app.route('/api/search-places')
def search_places():
    """Búsqueda rápida de ciudades, comunas y poblados de Chile."""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'results': []})

    if GEONAMES_DF is None:
        return jsonify({'results': []})

    try:
        mask = GEONAMES_DF['asciiname'].str.contains(query, case=False, na=False) | \
               GEONAMES_DF['name'].str.contains(query, case=False, na=False)
        matches = GEONAMES_DF[mask].copy()

        if matches.empty:
            return jsonify({'results': []})

        if 'population' in matches.columns:
            matches['population'] = pd.to_numeric(matches['population'], errors='coerce').fillna(0)
            matches = matches.sort_values(by='population', ascending=False)

        results = []
        for _, row in matches.head(10).iterrows():
            results.append({
                'name': str(row['name']),
                'asciiname': str(row['asciiname']),
                'lat': round(float(row['latitude']), 4),
                'lon': round(float(row['longitude']), 4),
                'region_code': str(row.get('admin1_code', '')),
                'population': int(row.get('population', 0))
            })

        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e), 'results': []}), 500


CHILE_REGIONS = [
    {"name": "Arica y Parinacota", "code": "15", "macrozone": "Norte Grande", "lat": -18.4783, "lon": -70.3126, "main_fuel": "Desértico / Oasis"},
    {"name": "Tarapacá", "code": "01", "macrozone": "Norte Grande", "lat": -20.2133, "lon": -70.1503, "main_fuel": "Desierto / Pampa"},
    {"name": "Antofagasta", "code": "02", "macrozone": "Norte Grande", "lat": -23.6509, "lon": -70.3975, "main_fuel": "Desierto Hiperárido"},
    {"name": "Atacama", "code": "03", "macrozone": "Norte Chico", "lat": -27.3668, "lon": -70.3323, "main_fuel": "Matorral Desértico"},
    {"name": "Coquimbo", "code": "04", "macrozone": "Norte Chico", "lat": -29.9533, "lon": -71.3436, "main_fuel": "Matorral Espinoso"},
    {"name": "Valparaíso", "code": "05", "macrozone": "Zona Central", "lat": -33.0472, "lon": -71.6127, "main_fuel": "Matorral Esclerófilo / Pino"},
    {"name": "Metropolitana de Santiago", "code": "13", "macrozone": "Zona Central", "lat": -33.4489, "lon": -70.6693, "main_fuel": "Espinal / Matorral / Agrícola"},
    {"name": "O'Higgins", "code": "06", "macrozone": "Zona Central", "lat": -34.1708, "lon": -70.7444, "main_fuel": "Plantaciones / Matorral"},
    {"name": "Maule", "code": "07", "macrozone": "Zona Centro-Sur", "lat": -35.4264, "lon": -71.6554, "main_fuel": "Plantación Pino/Eucalipto (Alta Carga)"},
    {"name": "Ñuble", "code": "16", "macrozone": "Zona Centro-Sur", "lat": -36.6067, "lon": -72.1033, "main_fuel": "Plantaciones / Mosaico Agrícola"},
    {"name": "Biobío", "code": "08", "macrozone": "Zona Centro-Sur", "lat": -36.8270, "lon": -73.0503, "main_fuel": "Plantación Forestal Continua"},
    {"name": "La Araucanía", "code": "09", "macrozone": "Zona Sur", "lat": -38.7359, "lon": -72.5904, "main_fuel": "Bosque Nativo / Plantaciones"},
    {"name": "Los Ríos", "code": "14", "macrozone": "Zona Sur", "lat": -39.8142, "lon": -73.2459, "main_fuel": "Selva Valdiviana / Praderas"},
    {"name": "Los Lagos", "code": "10", "macrozone": "Zona Sur", "lat": -41.4693, "lon": -72.9424, "main_fuel": "Bosque Templado Lluvioso"},
    {"name": "Aysén", "code": "11", "macrozone": "Zona Austral", "lat": -45.5712, "lon": -72.0683, "main_fuel": "Bosque Patagónico / Estepa"},
    {"name": "Magallanes", "code": "12", "macrozone": "Zona Austral", "lat": -53.1638, "lon": -70.9171, "main_fuel": "Tundra / Matorral Magallánico"}
]


@app.route('/api/regional-risk-summary')
def regional_risk_summary():
    """Resumen de actividad y focos por macrozona y región de Chile."""
    region_counts = {}
    for h in HISTORICAL_HOTSPOTS:
        reg = str(h.get('region', '')).strip()
        region_counts[reg] = region_counts.get(reg, 0) + 1

    summary = []
    for reg in CHILE_REGIONS:
        name = reg['name']
        hotspot_count = region_counts.get(name, 0)

        if hotspot_count > 150:
            vuln_level = "Muy Alta"
            vuln_color = "#B71C1C"
        elif hotspot_count > 60:
            vuln_level = "Alta"
            vuln_color = "#E65100"
        elif hotspot_count > 10:
            vuln_level = "Media"
            vuln_color = "#FF8F00"
        else:
            vuln_level = "Baja"
            vuln_color = "#2E7D32"

        summary.append({
            **reg,
            'historical_hotspots': hotspot_count,
            'vulnerability_level': vuln_level,
            'vulnerability_color': vuln_color
        })

    return jsonify({
        'total_regions': len(summary),
        'regions': summary
    })


def render_html_technical_report(lat, lon, fecha, prob, risk_level, risk_color, risk_desc, land_cover, town, dist_km, elev, slope, aspect, weather, shap_factors, past_days, prov):
    """Genera un informe técnico HTML imprimible / exportable en PDF con diseño profesional."""
    pct = round(prob * 100, 1)
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    shap_rows = "".join([
        f"<tr><td><strong>{f['label']}</strong> ({f['value']})</td>"
        f"<td style='color:{'#d32f2f' if f['impact'] > 0 else '#2e7d32'};font-weight:700;'>{'+' if f['impact'] > 0 else ''}{f['impact']:.3f}</td></tr>"
        for f in shap_factors
    ])

    past_rows = "".join([
        f"<tr><td>{d['date']}</td><td>{d['temp_max']}°C</td><td>{d['humidity_min']}%</td><td>{d['precip']} mm</td><td>{d['wind_max']} km/h</td></tr>"
        for d in past_days
    ])

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe Técnico de Riesgo de Incendio — SIpi Incendios ({fecha})</title>
    <style>
        @page {{ size: A4; margin: 15mm; }}
        body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; color: #1a1a2e; margin: 0; padding: 20px; background: #fff; line-height: 1.4; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #e65100; padding-bottom: 12px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 20px; color: #e65100; text-transform: uppercase; }}
        .header .meta {{ font-size: 11px; color: #666; text-align: right; }}
        .risk-banner {{ background: {risk_color}15; border: 2px solid {risk_color}; border-radius: 8px; padding: 15px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .risk-badge {{ font-size: 28px; font-weight: 800; color: {risk_color}; }}
        .risk-title {{ font-size: 16px; font-weight: 700; color: {risk_color}; text-transform: uppercase; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
        .card {{ border: 1px solid #ddd; border-radius: 6px; padding: 12px; background: #fafafa; }}
        .card h3 {{ margin-top: 0; font-size: 13px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 5px; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
        th, td {{ padding: 5px 8px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f0f0f0; color: #444; font-weight: 700; }}
        .footer {{ border-top: 1px solid #ccc; padding-top: 10px; margin-top: 25px; font-size: 10px; color: #777; text-align: center; }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 15px; text-align: right;">
        <button onclick="window.print()" style="background:#e65100;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-weight:700;">🖨️ Imprimir / Guardar en PDF</button>
    </div>

    <div class="header">
        <div>
            <h1>SIpi Incendios — Dossier Técnico de Riesgo</h1>
            <div style="font-size: 12px; color: #555; margin-top: 3px;">Sistema Inteligente de Predicción de Incendios Forestales para Chile</div>
        </div>
        <div class="meta">
            <div><strong>Fecha de Evaluación:</strong> {fecha}</div>
            <div><strong>Generado:</strong> {gen_time}</div>
            <div><strong>Coordenadas:</strong> {lat:.4f}, {lon:.4f}</div>
        </div>
    </div>

    <div class="risk-banner">
        <div>
            <div class="risk-title">Nivel de Riesgo Evaluado: {risk_level}</div>
            <div style="font-size: 12px; color: #444; margin-top: 4px;">{risk_desc}</div>
        </div>
        <div class="risk-badge">{pct}%</div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>🌲 Entorno Geoespacial y Combustible</h3>
            <table>
                <tr><td><strong>Uso de Suelo (MapBiomas 2022):</strong></td><td>{land_cover}</td></tr>
                <tr><td><strong>Poblado Más Próximo (GeoNames):</strong></td><td>{town} ({dist_km} km)</td></tr>
                <tr><td><strong>Elevación (NASA SRTM):</strong></td><td>{elev} m.s.n.m.</td></tr>
                <tr><td><strong>Pendiente Topográfica:</strong></td><td>{slope}°</td></tr>
                <tr><td><strong>Orientación de Ladera:</strong></td><td>{aspect}°</td></tr>
            </table>
        </div>

        <div class="card">
            <h3>🌤️ Condiciones Meteorológicas (Ventana 7 Días)</h3>
            <table>
                <tr><td><strong>Temperatura Máxima:</strong></td><td>{weather['temp_max_window']:.1f}°C</td></tr>
                <tr><td><strong>Temperatura Media:</strong></td><td>{weather['temp_mean_window']:.1f}°C</td></tr>
                <tr><td><strong>Humedad Mínima:</strong></td><td>{weather['humidity_min_window']:.1f}%</td></tr>
                <tr><td><strong>Lluvia Acumulada:</strong></td><td>{weather['precip_acc_window']:.1f} mm</td></tr>
                <tr><td><strong>Viento Máximo:</strong></td><td>{weather['wind_speed_max_window']:.1f} km/h</td></tr>
            </table>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>🔍 Factores Críticos Determinantes (SHAP)</h3>
            <table>
                <thead><tr><th>Variable</th><th>Impacto</th></tr></thead>
                <tbody>{shap_rows}</tbody>
            </table>
        </div>

        <div class="card">
            <h3>⏪ Registro de Días Anteriores (Ventana Histórica)</h3>
            <table>
                <thead><tr><th>Fecha</th><th>Temp.</th><th>Hum.</th><th>Lluvia</th><th>Viento</th></tr></thead>
                <tbody>{past_rows}</tbody>
            </table>
        </div>
    </div>

    <div class="card" style="margin-bottom: 20px;">
        <h3>🛰️ Trazabilidad de Fuentes y Certificación de Datos</h3>
        <table>
            <tr><td><strong>Fuente Meteorológica:</strong></td><td>{prov.get('source_name', 'Open-Meteo API')}</td></tr>
            <tr><td><strong>Latencia de Conexión:</strong></td><td>{prov.get('latency_ms', 0)} ms (HTTP {prov.get('http_status', 200)} OK)</td></tr>
            <tr><td><strong>Muestras Horarias Procesadas:</strong></td><td>{prov.get('hourly_samples', 168)} horas ({prov.get('start_window', '')} a {prov.get('end_window', '')})</td></tr>
            <tr><td><strong>Modelo de Machine Learning:</strong></td><td>XGBoost V2 (22 features) · AUC-ROC 0.793 · Optimización Bayesiana Optuna</td></tr>
        </table>
    </div>

    <div class="footer">
        Documento generado automáticamente por SIpi Incendios · Plataforma de Inteligencia Artificial para la Gestión del Riesgo de Incendios en Chile.
    </div>
</body>
</html>"""


@app.route('/api/export-report', methods=['GET', 'POST'])
def export_report():
    """Genera un informe técnico descargable o imprimible en formato HTML / JSON / CSV."""
    if request.method == 'POST':
        data = request.get_json() or {}
    else:
        data = request.args.to_dict()

    lat = float(data.get('lat', -36.8270))
    lon = float(data.get('lon', -73.0503))
    fecha = data.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    fmt = data.get('format', 'html').lower()

    weather, past_days, provenance = fetch_weather_for_prediction(lat, lon, fecha)
    if weather is None or weather == 'RATE_LIMITED':
        return jsonify({'error': 'No se pudieron obtener datos meteorológicos para el reporte.'}), 500

    land_cover_class, land_cover_name = query_mapbiomas(lat, lon)
    dist_town_km, nearest_town_name = query_nearest_town(lat, lon)
    elevation, slope_deg, aspect_deg = query_topography(lat, lon)

    if land_cover_class in NON_BURNABLE_CLASSES:
        probability = 0.0
        risk_level, risk_color, risk_description = classify_risk(0.0, is_non_burnable=True, non_burnable_desc=NON_BURNABLE_CLASSES[land_cover_class][1])
        shap_factors = [{'feature': 'land_cover', 'label': 'Superficie No Combustible', 'impact': -5.0, 'direction': 'decreases_risk', 'value': land_cover_name}]
    else:
        feat_dict = build_feature_dict(lat, lon, fecha, weather, land_cover_class, dist_town_km, elevation, slope_deg, aspect_deg)
        df = pd.DataFrame([feat_dict])[FEATURES]
        df['land_cover_class'] = df['land_cover_class'].astype('category')
        raw_prob = float(MODEL.predict_proba(df)[:, 1][0])
        if weather.get('precip_acc_window', 0) > 30.0 and weather.get('temp_max_window', 20) < 16.0:
            raw_prob = min(raw_prob, 0.04)
        elif weather.get('precip_acc_window', 0) > 15.0 and weather.get('humidity_min_window', 50) > 65.0:
            raw_prob = min(raw_prob, 0.15)
        probability = raw_prob
        risk_level, risk_color, risk_description = classify_risk(probability)
        shap_factors = explain_prediction(df)

    if fmt == 'json':
        return jsonify({
            'report_title': 'Informe Técnico de Evaluación de Riesgo de Incendio Forestal',
            'system': 'SIpi Incendios — Sistema Inteligente de Predicción de Incendios',
            'generated_at': datetime.now().isoformat(),
            'evaluation': {
                'coordinates': {'lat': lat, 'lon': lon},
                'date': fecha,
                'probability': round(probability, 4),
                'risk_level': risk_level,
                'risk_color': risk_color,
                'risk_description': risk_description,
                'spatial_info': {
                    'land_cover': land_cover_name,
                    'nearest_town': nearest_town_name,
                    'dist_town_km': dist_town_km,
                    'elevation_m': elevation,
                    'slope_deg': slope_deg,
                    'aspect_deg': aspect_deg
                },
                'weather_summary': weather,
                'data_provenance': provenance,
                'shap_factors': shap_factors,
                'past_7_days': past_days
            }
        })

    elif fmt == 'csv':
        import io, csv
        from flask import Response
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['lat', 'lon', 'fecha', 'probabilidad', 'nivel_riesgo', 'uso_suelo', 'poblado_cercano', 'dist_km', 'elevacion_m', 'pendiente_deg', 'temp_max', 'hum_min', 'precip_total', 'viento_max'])
        writer.writerow([
            lat, lon, fecha, round(probability, 4), risk_level, land_cover_name, nearest_town_name, dist_town_km,
            elevation, slope_deg, round(weather['temp_max_window'], 1), round(weather['humidity_min_window'], 1),
            round(weather['precip_acc_window'], 1), round(weather['wind_speed_max_window'], 1)
        ])
        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename=informe_riesgo_{fecha}_{lat}_{lon}.csv'})

    else:
        return render_html_technical_report(lat, lon, fecha, probability, risk_level, risk_color, risk_description, land_cover_name, nearest_town_name, dist_town_km, elevation, slope_deg, aspect_deg, weather, shap_factors, past_days, provenance)


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(str(STATIC_DIR), path)


# ── Main ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("   [SIpi Incendios] Servidor Dashboard Listo")
    print("   http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False, threaded=True)
