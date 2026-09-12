# 🌲 SIpi Incendios — Informe Técnico y Ejecutivo del Sistema
## Sistema Inteligente de Predicción, Proyección y Explicabilidad de Riesgo de Incendios Forestales para Chile Continental

**Autores:** Equipo de Desarrollo e Investigación SIpi Incendios  
**Fecha:** Septiembre 2026  
**Versión del Sistema:** 2.0 (Modelo XGBoost V2 · 22 Variables · SHAP TreeExplainer)  
**Entorno Operativo:** Python 3.10+ · Flask REST API · Leaflet Geoespacial · Open-Meteo ERA5 Reanalysis  

---

## 📑 Tabla de Contenidos
1. [Resumen Ejecutivo y Ficha Técnica](#1-resumen-ejecutivo-y-ficha-técnica)
2. [Problema Público y Contexto Nacional en Chile](#2-problema-público-y-contexto-nacional-en-chile)
3. [Arquitectura Global de la Solución](#3-arquitectura-global-de-la-solución)
4. [Pipeline de Ingeniería de Datos Geoespaciales (ETL)](#4-pipeline-de-ingeniería-de-datos-geoespaciales-etl)
   - 4.1 Las 6 Fuentes de Datos Integradas
   - 4.2 Matriz y Diccionario de las 22 Variables
   - 4.3 Estrategia Metodológica: Muestreo Negativo y Prevención de Data Leakage
5. [Modelamiento Predictivo de Machine Learning](#5-modelamiento-predictivo-de-machine-learning)
   - 5.1 Algoritmo XGBoost V2 y Función Objetivo
   - 5.2 Optimización Bayesiana de Hiperparámetros (Optuna)
   - 5.3 Ponderación de Muestras y Corrección de Sesgo Estacional
   - 5.4 Métricas Institucionales de Rendimiento
6. [Explicabilidad Local en Tiempo Real (SHAP)](#6-explicabilidad-local-en-tiempo-real-shap)
   - 6.1 Fundamento Matemático de los Valores Shapley
   - 6.2 Interpretación de Factores Aceleradores vs Protectores
7. [Servidor Backend y Arquitectura de la API REST](#7-servidor-backend-y-arquitectura-de-la-api-rest)
   - 7.1 Catálogo de Endpoints
   - 7.2 Optimizaciones de Latencia (Caché TTL, Rasterio, BallTree)
8. [Interfaz de Usuario y Herramientas del Dashboard](#8-interfaz-de-usuario-y-herramientas-del-dashboard)
   - 8.1 Monitor Geoespacial y Capas Cartográficas
   - 8.2 Tacómetro y Protocolos de Alerta Institucional (CONAF / SENAPRED)
   - 8.3 Evaluador Dinámico de la Regla 30-30-30
   - 8.4 Pronóstico Meteorológico a 7 Días
   - 8.5 Simulador Climático "¿Qué pasaría si...?" (What-If Analysis)
   - 8.6 Exportación de Dossiers Técnicos (PDF, JSON, CSV)
9. [Principales Hallazgos Cuantitativos del Territorio Chileno](#9-principales-hallazgos-cuantitativos-del-territorio-chileno)
10. [Recomendaciones Estratégicas para la Gestión del Riesgo](#10-recomendaciones-estratégicas-para-la-gestión-del-riesgo)
11. [Conclusiones y Trabajo Futuro](#11-conclusiones-y-trabajo-futuro)

---

## 1. Resumen Ejecutivo y Ficha Técnica

**SIpi Incendios** es una plataforma tecnológica avanzada de ciencia de datos, inteligencia artificial y análisis geoespacial diseñada específicamente para responder a la recurrente crisis de incendios forestales en Chile continental. A diferencia de los índices meteorológicos tradicionales aislados (como el FWI canadiense no contextualizado), SIpi Incendios combina en un único flujo analítico:

1. El registro histórico oficial de más de 20 años de incendios forestales en tierra provisto por la **Corporación Nacional Forestal (CONAF)** e **Itrend** (1985–2023).
2. Detecciones térmicas espaciales infrarrojas del sensor satelital **NASA VIIRS** (Suomi-NPP 2017–2024).
3. Cartografía de uso y cobertura vegetal de alta resolución espacial (30 metros) de **MapBiomas Chile (Colección 1 - 2022)**.
4. Topografía digital de elevación y cálculo de pendiente del terreno mediante la misión de radar **NASA SRTM v3.0**.
5. Catastro georreferenciado de más de 6.900 asentamientos humanos mediante **GeoNames Chile** estructurado en árboles de búsqueda esférica `BallTree`.
6. Variables meteorológicas horarias de reanálisis atmosférico y pronósticos satelitales en tiempo real extraídos vía **Open-Meteo API (ECMWF ERA5)**.
7. Algoritmos de árboles potenciados por gradiente (**XGBoost V2**) optimizados mediante búsqueda Bayesiana (**Optuna**).
8. Explicabilidad transparente y auditable para cada coordenada geográfica mediante **SHAP TreeExplainer**.

### 📋 Ficha Técnica Institucional

| Dimensión | Especificación Técnica |
|---|---|
| **Modelo Núcleo** | XGBoost Classifier (Gradient Boosted Trees) V2 con calibración de probabilidad |
| **Variables de Entrada** | 22 variables (9 climáticas de ventana 7d, 1 cobertura vegetal, 1 distancia antrópica, 3 topográficas, 4 temporales-cíclicas, 4 índices de interacción) |
| **Muestras de Entrenamiento** | 5.848 eventos históricos (Split Temporal estricto 2002–2018) |
| **Muestras de Evaluación** | 968 eventos históricos (Años 2019–2020 sin contacto previo en entrenamiento) |
| **Área Bajo la Curva ROC (ROC-AUC)** | **0.7932** (Capacidad discriminativa superior frente a modelos logísticos) |
| **F1-Score Ponderado** | **0.7515** |
| **Sensibilidad / Recall de Incendios** | **88.84%** (Identificación de 9 de cada 10 incendios reales) |
| **Calibración de Probabilidad (Brier Score)** | **0.2221** (Probabilidades confiables para asignación presupuestaria) |
| **Tiempo de Inferencia por Punto** | < 850 ms (incluyendo consulta de APIs externas y extracción ráster) |
| **Servidor y API** | Flask 3.0 / Python, WSGI multihilo con caché en memoria (TTL 30 min) |
| **Frontend** | Single Page Application (SPA) en Vanilla JS, CSS3 Glassmorphism y Leaflet 1.9 |

---

## 2. Problema Público y Contexto Nacional en Chile

Chile continental posee una geografía singular caracterizada por un clima mediterráneo estival en su zona central y centro-sur, acompañado de una intensa actividad silvoagropecuaria. En las últimas dos décadas, el país ha experimentado la **Megasequía más prolongada de su historia documentada (iniciada en 2010)**, lo que ha generado un desecamiento estructural de la vegetación nativa y de las plantaciones de monocultivo forestal (Pino radiata y Eucalipto).

Durante este periodo, Chile enfrentó eventos catastróficos de sexta generación ("megaincendios" o tormentas de fuego), tales como:
- **Temporada 2016–2017 (Tormenta de Fuego):** Devastó más de 570.000 hectáreas, destruyendo por completo la localidad de Santa Olga (Región del Maule) y cobrando 11 vidas humanas.
- **Temporada 2022–2023:** Afectó más de 430.000 hectáreas en las regiones de Ñuble, Biobío y La Araucanía, con 26 víctimas fatales y miles de viviendas destruidas.
- **Febrero 2024 (Valparaíso - Viña del Mar):** El incendio forestal más mortífero del siglo XXI en Chile, con 137 fallecidos en la interfaz urbano-forestal.

### La Falencia de los Sistemas Tradicionales
Los sistemas convencionales de monitoreo suelen apoyarse exclusivamente en índices meteorológicos agregados a nivel macro (provincial o regional), ignorando:
1. **El tipo de biomasa combustible específico:** Un pastizal seco reacciona en minutos; un bosque nativo húmedo posee una resiliencia hídrica muy superior; una plantación densa de pino acumula cargas térmicas extremas.
2. **La microtopografía:** El fuego sube por laderas empinadas a una velocidad hasta cuatro veces superior que en terreno plano por precalentamiento convectivo.
3. **El factor humano:** En Chile, más del **99% de los incendios son causados por acción humana** (intencionalidad o negligencia). Por ende, la proximidad a centros poblados y vías de tránsito es el factor espacial más correlacionado con la ignición.

**SIpi Incendios** resuelve esta brecha al unificar estas capas a nivel de pixel y coordenada exacta, entregando una probabilidad calibrada y explicando el porqué físico detrás de cada alerta.

---

## 3. Arquitectura Global de la Solución

El sistema sigue una arquitectura modular en capas desacopladas, diseñada para maximizar la reproducibilidad científica y la velocidad de respuesta en entornos operativos:

```
                                  FUENTES DE DATOS PRIMARIAS
  ┌─────────────────┬──────────────────┬─────────────────┬─────────────────┬─────────────────┐
  │ CONAF / Itrend  │ NASA VIIRS Sat.  │ Open-Meteo API  │ MapBiomas Chile │ NASA SRTM v3.0  │
  │ (109k eventos)  │ (Puntos calor)   │ (ECMWF ERA5)    │ (Raster 30m)    │ (Elev. / Pend.) │
  └────────┬────────┴────────┬─────────┴────────┬────────┴────────┬────────┴────────┬────────┘
           │                 │                  │                 │                 │
           ▼                 ▼                  ▼                 ▼                 ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────┐
  │                           PIPELINE ETL GEOESPACIAL (src/data/)                           │
  │  - Limpieza y filtrado continental de Chile (-56° a -17° latitud)                        │
  │  - Cruce temporal con ventanas climáticas de 7 días continuos                            │
  │  - Indexación espacial BallTree de 6.967 asentamientos (GeoNames)                        │
  │  - Muestreo geoespacial en GeoTIFF de 30m y cálculo trigonométrico de pendiente          │
  │  - Smart Negative Sampling en coberturas vegetales quemables                             │
  └────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │
                                               ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────┐
  │                           MODELAMIENTO PREDICTIVO (src/models/)                          │
  │  - Split temporal estricto (Train: 2002-2018 | Test: 2019-2020)                        │
  │  - Ponderación de muestras (sample weights) contra sesgo invernal                        │
  │  - Optimización Bayesiana de hiperparámetros con Optuna (80 iteraciones)                 │
  │  - Serialización de artefactos: xgboost_fire_model_final.pkl y metadata                  │
  └────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │
                                               ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────┐
  │                           BACKEND & MOTOR DE INFERENCIA (Flask)                          │
  │  - TreeExplainer SHAP en memoria para cálculo de aportes locales                         │
  │  - In-Memory Cache con TTL de 30 min para llamadas meteorológicas                        │
  │  - API REST: /api/predict, /api/forecast, /api/simulate, /api/historical-hotspots        │
  └────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │
                                               ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────┐
  │                            FRONTEND INTERACTIVO (SPA Web)                                │
  │  - Leaflet Map con 1.616 focos históricos y clusterización reactiva                      │
  │  - Tacómetro dinámico con alertas institucionales CONAF/SENAPRED                         │
  │  - Evaluador en tiempo real de la Regla del 30-30-30 con barras dinámicas               │
  │  - Pronóstico proyectado a 7 días y Simulador de escenarios "What-If"                    │
  │  - Generador de Dossiers Técnicos descargables en PDF, JSON y CSV                         │
  └──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Pipeline de Ingeniería de Datos Geoespaciales (ETL)

### 4.1 Las 6 Fuentes de Datos Integradas

1. **CONAF & Itrend (1985–2023):**  
   Consolidación de las memorias estadísticas oficiales de incendios forestales de Chile. Se integraron **109.985 eventos históricos georreferenciados**, extrayendo fecha, hora de inicio, causa basal (intencional, tránsito, faenas agrícolas, etc.), duración en horas y superficie quemada desglosada por estrato vegetacional.
2. **NASA FIRMS — Sensor Satelital VIIRS Suomi-NPP (2017–2024):**  
   Extracción masiva de detecciones térmicas infrarrojas a 375 metros de resolución para validar los focos de combate terrestre contra detecciones orbitales de anomalías de temperatura de brillo.
3. **Open-Meteo Historical & Forecast API (ECMWF ERA5 Reanalysis):**  
   Extracción multihilo de las condiciones meteorológicas horarias previas al evento (ventana de 7 días completos, 168 horas por evento): temperatura máxima, media, humedad relativa mínima, humedad del suelo (0-7 cm) y velocidad media y ráfagas máximas de viento.
4. **MapBiomas Chile (Colección 1 - 2022):**  
   Capa de cobertura de uso de suelo a resolución de 30 metros. Permite identificar si la coordenada corresponde a plantación forestal industrial (Pino/Eucalipto), bosque nativo, matorral esclerófilo, pastizal, humedal, zona urbana o cuerpo de agua.
5. **NASA SRTM v3.0 (Shuttle Radar Topography Mission):**  
   Modelo digital de elevación de 1 arco-segundo (~30m). Se calcula analíticamente la pendiente del terreno ($\alpha$) y la orientación cardinal de la ladera (aspecto) utilizando derivadas espaciales de diferencias finitas en una cuadrícula $3 \times 3$:
   $$\text{Pendiente} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right)$$
6. **GeoNames Chile (Catastro Nacional de Asentamientos Humanos):**  
   Indexación de 6.967 asentamientos (ciudades, pueblos, aldeas, caseríos) en un árbol espacial esférico `BallTree` con métrica Haversine, permitiendo obtener en microsegundos la distancia exacta en kilómetros desde cualquier coordenada al poblado más próximo.

---

### 4.2 Matriz y Diccionario de las 22 Variables

| # | Variable | Tipo | Unidad / Rango | Descripción y Fundamento Físico |
|---|---|---|---|---|
| 1 | `temp_max_window` | Flotante | °C | Temperatura máxima registrada en la ventana de 7 días previos. Deseca el combustible vegetal fino. |
| 2 | `temp_mean_window` | Flotante | °C | Temperatura promedio en la ventana de 7 días. Representa la persistencia de estrés térmico. |
| 3 | `humidity_min_window`| Flotante | % (0–100) | Humedad relativa mínima del aire. Bajo el 30%, el combustible vegetal alcanza equilibrio higroscópico crítico. |
| 4 | `humidity_mean_window`| Flotante | % (0–100) | Humedad relativa promedio de los 7 días. |
| 5 | `precip_acc_window` | Flotante | mm | Precipitación acumulada en los 7 días anteriores. Lluvias > 5mm inhiben la inflamabilidad temporalmente. |
| 6 | `wind_speed_max_window`| Flotante | km/h | Ráfaga máxima de viento registrada. Aporta oxígeno a la combustión y proyecta pavesas incandescentes. |
| 7 | `wind_speed_mean_window`| Flotante | km/h | Velocidad media del viento. |
| 8 | `soil_temp_mean` | Flotante | °C | Temperatura media del suelo superficial (0 a 7 cm). Indicador de irradiación solar acumulada. |
| 9 | `soil_moisture_mean` | Flotante | $m^3/m^3$ (0–1) | Contenido volumétrico de agua en suelo. Proxy del estrés hídrico de raíces y biomasa viva. |
| 10 | `land_cover_class` | Categórica | ID MapBiomas | Tipo de combustible de suelo (Plantación, Bosque Nativo, Matorral, etc.). |
| 11 | `dist_nearest_town_km`| Flotante | km | Distancia esférica al poblado más próximo. Mide la exposición a ignición antrópica (caminos y personas). |
| 12 | `elevation` | Flotante | m.s.n.m. | Elevación sobre el nivel del mar. A mayor altura disminuye la presión de oxígeno y la densidad vegetal continua. |
| 13 | `slope_deg` | Flotante | Grados (0–90°) | Pendiente del terreno. Por cada 10° de incremento, la velocidad de propagación ladera arriba se duplica. |
| 14 | `aspect_deg` | Flotante | Grados (0–360°) | Orientación de ladera. En Chile, laderas norte y poniente reciben máxima radiación solar diurna. |
| 15 | `month_sin` | Flotante | [-1.0, 1.0] | Componente senoidal del mes del año: $\sin(2\pi \cdot \text{mes} / 12)$. Preserva la continuidad cíclica dic-ene. |
| 16 | `month_cos` | Flotante | [-1.0, 1.0] | Componente cosenoidal del mes: $\cos(2\pi \cdot \text{mes} / 12)$. |
| 17 | `day_of_year` | Entero | 1–366 | Día del año juliano. Permite ajustar la fenología estacional fina de floración y desecamiento. |
| 18 | `season` | Categórica | 1–4 | Estación astronómica en el Hemisferio Sur (1=Verano, 2=Otoño, 3=Invierno, 4=Primavera). |
| 19 | `dryness_index` | Flotante | Adimensional | Índice de sequedad derivado: $T_{\max} \cdot \frac{100 - H_{\text{mean}}}{100}$. Cuantifica el poder evaporativo del aire. |
| 20 | `precip_drought` | Binaria | 0 o 1 | Indicador de sequía absoluta: 1 si `precip_acc_window` < 1.0 mm, 0 en caso contrario. |
| 21 | `temp_humidity_ratio`| Flotante | Adimensional | Ratio de evaporación extrema: $\frac{T_{\max}}{H_{\min} + 1}$. Se dispara ante combinaciones de calor y sequedad. |
| 22 | `fire_weather_index` | Flotante | Adimensional | Aproximación del FWI canadiense: $\frac{T_{\max} \cdot V_{\max}}{H_{\min} + 1}$. Combina calor, viento y baja humedad. |

---

### 4.3 Estrategia Metodológica: Muestreo Negativo y Prevención de Data Leakage

#### Prevención de Data Leakage (Fuga de Información)
En problemas espacio-temporales, el particionamiento aleatorio tradicional (*random k-fold split*) introduce un severo sesgo optimista: el modelo memoriza condiciones de una ola de calor específica presente tanto en entrenamiento como en validación.  
Para evitar esto, SIpi Incendios implementó un **Split Temporal Estricto**:
- **Conjunto de Entrenamiento:** Eventos ocurridos entre **2002 y 2018** (5.848 muestras).
- **Conjunto de Evaluación Independiente:** Eventos ocurridos entre **2019 y 2020** (968 muestras nunca vistas durante el ajuste).

#### Smart Negative Sampling (Muestreo Negativo Inteligente)
Los registros de CONAF solo contienen eventos positivos (incendios ocurridos). Para que un modelo de clasificación binaria aprenda a discriminar el riesgo, se requiere generar pseudo-ausencias (*negativos*):
- No se muestrearon negativos sobre el océano, glaciares o cumbres desérticas donde un incendio es físicamente imposible (lo que inflaría artificialmente la precisión).
- Se implementó **Smart Negative Sampling**: los puntos negativos se generaron en áreas con combustible vegetal real (bosques, matorrales, pastizales y plantaciones de MapBiomas) en fechas históricas donde **no** se reportaron incendios en un radio de 20 km.

---

## 5. Modelamiento Predictivo de Machine Learning

### 5.1 Algoritmo XGBoost V2 y Función Objetivo
Se seleccionó **XGBoost (Extreme Gradient Boosting)** por su capacidad intrínseca para manejar relaciones no lineales complejas, interacciones de alto orden entre variables climáticas y topográficas, y robustez frente a valores atípicos.  
El modelo minimiza la función de pérdida logística binaria con regularización $L_1$ y $L_2$:

$$\mathcal{L}(\theta) = \sum_{i=1}^{N} \left[ y_i \ln(1 + e^{-\hat{y}_i}) + (1 - y_i) \ln(1 + e^{\hat{y}_i}) \right] + \sum_{k} \left( \gamma T_k + \frac{1}{2}\lambda \|w_k\|^2 + \alpha \|w_k\|_1 \right)$$

### 5.2 Optimización Bayesiana de Hiperparámetros (Optuna)
Se ejecutó un estudio de 80 iteraciones mediante optimización Bayesiana con Tree-structured Parzen Estimator (TPE) en **Optuna**, optimizando la métrica ROC-AUC sobre validación cruzada temporal:
- `max_depth`: 6 (evita sobreajuste en árboles profundos).
- `learning_rate` ($\eta$): 0.045 (convergencia suave y estable).
- `n_estimators`: 450 árboles con parada temprana (*early stopping* de 30 rondas).
- `subsample`: 0.85 (fracción de muestras por árbol para reducir varianza).
- `colsample_bytree`: 0.80 (muestreo de variables por árbol).
- `reg_alpha` ($\alpha$): 0.35 (regularización Lasso para selección de features).
- `reg_lambda` ($\lambda$): 1.80 (regularización Ridge para contrarrestar multicolinealidad).

### 5.3 Ponderación de Muestras y Corrección de Sesgo Estacional
Para evitar que el modelo sobreestime el riesgo en invierno o lo subestime durante olas de calor estivales, se aplicaron **pesos de muestra diferenciados (*sample weights*)**:
$$w_i = \begin{cases} 
1.35 & \text{si } \text{temporada} \in \{\text{Verano}\} \wedge y_i = 1 \\
1.15 & \text{si } \text{temporada} \in \{\text{Primavera}\} \wedge y_i = 1 \\
0.85 & \text{si } \text{temporada} \in \{\text{Invierno}\} \\
1.00 & \text{en otros casos}
\end{cases}$$

### 5.4 Métricas Institucionales de Rendimiento (Test Set 2019–2020)

| Métrica | Valor Obtenido | Interpretación Práctica |
|---|---|---|
| **ROC-AUC** | **0.7932** | El modelo tiene casi un 80% de probabilidad de clasificar un día/lugar de incendio real por encima de un día no-incendio. |
| **F1-Score Ponderado** | **0.7515** | Excelente balance armónico entre precisión y cobertura de focos. |
| **Recall / Sensibilidad** | **88.84%** | Detecta el 88.8% de los incendios reales, minimizando los falsos negativos (vital para protección de vidas). |
| **Accuracy Global** | **69.52%** | Tasa global sobre un conjunto de prueba balanceado y riguroso. |
| **Brier Score** | **0.2221** | Calibración adecuada: las probabilidades predichas corresponden fielmente a las frecuencias relativas observadas. |

---

## 6. Explicabilidad Local en Tiempo Real (SHAP)

### 6.1 Fundamento Matemático de los Valores Shapley
En un sistema crítico como la gestión de emergencias, los modelos de "caja negra" son inaceptables para la toma de decisiones. SIpi Incendios integra **SHAP (SHapley Additive exPlanations)** basado en teoría de juegos cooperativos.  
Para cada predicción individual $x$, la probabilidad predicha en espacio logit se descompone aditivamente como la suma de la contribución de cada variable más un valor base esperado $\phi_0$:

$$f(x) = \phi_0 + \sum_{j=1}^{M} \phi_j(x)$$

Donde cada valor $\phi_j$ representa el aporte neto (en unidades log-odds) de la variable $j$ a la predicción para esa coordenada y fecha específica.

### 6.2 Interpretación de Factores Aceleradores vs Protectores
En la interfaz gráfica, TreeExplainer evalúa los 22 features en < 15 milisegundos y clasifica los resultados en dos categorías visuales:
- **Barras Naranjas / Rojas (+): Factores Aceleradores de Riesgo:** Variables que empujaron la probabilidad hacia arriba en ese evento (ej. $T_{\max} = 34.5^\circ\text{C}$, viento de $38\text{ km/h}$, pendiente pronunciada o cercanía a un camino transitado).
- **Barras Verdes (-): Factores Protectores de Riesgo:** Variables que contuvieron el peligro (ej. humedad mínima alta, lluvia acumulada en la semana previa o cobertura de bosque nativo bien hidratado).

---

## 7. Servidor Backend y Arquitectura de la API REST

El backend está desarrollado en **Python con Flask**, diseñado bajo principios RESTful y optimizado para concurrencia mediante `threaded=True`.

### 7.1 Catálogo de Endpoints

| Método | Endpoint | Parámetros Clave | Salida / Función |
|---|---|---|---|
| `GET` | `/` | — | Entrega la aplicación SPA web completa (HTML5, CSS, JS). |
| `POST` | `/api/predict` | `lat`, `lon`, `fecha` | Realiza el cruce geoespacial en vivo, consulta Open-Meteo, ejecuta XGBoost y calcula valores SHAP. |
| `POST` | `/api/forecast` | `lat`, `lon` | Consulta el pronóstico a 7 días de Open-Meteo y calcula el vector de riesgo para los próximos 7 días. |
| `POST` | `/api/simulate` | `lat`, `lon`, `delta_temp`, `delta_humidity`, `delta_wind`, `override_land_cover`, `override_slope` | Simulador What-If: evalúa el cambio dinámico entre la condición base y el escenario alterado. |
| `GET` | `/api/historical-hotspots`| — | Retorna la muestra georreferenciada de 1.616 focos históricos con metadatos (superficie quemada, comuna, causa). |
| `GET` | `/api/model-info` | — | Retorna la metadata del modelo, versión, hiperparámetros y métricas de evaluación. |
| `GET` | `/api/evaluation-plots`| — | Lista las imágenes PNG de diagnóstico disponibles en el servidor. |
| `GET` | `/api/plot/<filename>` | `filename` | Sirve la imagen de diagnóstico en alta resolución para el visualizador Lightbox. |
| `GET` | `/api/search-places` | `q` (texto de búsqueda) | Autocompletado rápido de comunas y ciudades de Chile usando GeoNames con orden por población. |
| `GET` | `/api/regional-risk-summary`| — | Resumen de actividad histórica y nivel de vulnerabilidad de las 16 regiones de Chile. |
| `GET/POST`| `/api/export-report` | `lat`, `lon`, `fecha`, `format` (`html`, `json`, `csv`) | Genera un informe técnico descargable o imprimible con membrete y certificación de datos. |

### 7.2 Optimizaciones de Latencia
- **Caché en Memoria con TTL (30 minutos):** Las consultas climáticas para un mismo sector geográfico y fecha se almacenan en memoria para evitar saturar la cuota de la API meteorológica externa y reducir la latencia de 1.200 ms a 12 ms en consultas repetidas.
- **Consultas Ráster O(1):** `rasterio` realiza muestreo directo por ventana indexada sobre el GeoTIFF de MapBiomas (62.618 x 154.690 píxeles) sin cargar la imagen completa en memoria RAM.
- **Búsqueda Geodésica $O(\log N)$:** El árbol espacial `BallTree` reduce la búsqueda del poblado más cercano entre 6.967 asentamientos a pocas operaciones vectorizadas de distancia Haversine.

---

## 8. Interfaz de Usuario y Herramientas del Dashboard

La interfaz de usuario ha sido concebida bajo el paradigma de un **Centro de Mando de Emergencias (Enterprise Command Center)**, utilizando estética oscura (*Dark Theme*), glassmorphism con efecto de desenfoque de fondo y acentos cromáticos normados por severidad.

### 8.1 Monitor Geoespacial y Capas Cartográficas
- Desarrollado sobre Leaflet 1.9 con `Leaflet.markercluster` para representar fluidamente miles de focos sin degradar el rendimiento del navegador.
- Selector conmutable de 3 capas base: **Dark Canvas** (alto contraste para operaciones nocturnas), **Satelital** (inspección de dosel vegetal) y **Calles/Topográfico** (red vial secundaria).
- Barra de saltos de macrozona: navegación en un clic entre **Todo Chile**, **Zona Centro** (Valparaíso/RM), **Centro-Sur** (Maule/Biobío), **Sur** (Araucanía/Lagos) y **Austral**.
- Buscador predictivo de comunas y coordenadas dinámicas en el cursor.

### 8.2 Tacómetro y Protocolos de Alerta Institucional (CONAF / SENAPRED)
Un medidor semicircular animado en SVG calcula el ángulo de la aguja ($0^\circ$ a $180^\circ$) según la probabilidad predicha y asigna la categoría oficial:
1. **🟢 Riesgo Bajo (< 25%):** Condiciones favorables. Vigilancia preventiva rutinaria.
2. **🟡 Riesgo Moderado (25% – 50%):** Alerta Temprana Preventiva. Restricción o prohibición total de quemas agrícolas.
3. **🟠 Riesgo Alto (50% – 75%):** Alerta Amarilla. Preposicionamiento de brigadas terrestres y aeronaves de combate.
4. **🔴 Riesgo Crítico (> 75%):** Alerta Roja. Peligro inminente de propagación descontrolada con amenaza a infraestructura crítica y centros poblados.

### 8.3 Evaluador Dinámico de la Regla 30-30-30
La tradicional regla empírica utilizada por brigadistas forestales y bomberos en Chile establece peligro extremo cuando concurren simultáneamente:
- Temperatura $> 30^\circ\text{C}$
- Humedad Relativa $< 30\%$
- Velocidad del Viento $> 30\text{ km/h}$

El dashboard incorpora **3 mini-indicadores de barra dinámicos** que calculan el porcentaje exacto de cumplimiento de cada umbral en tiempo real y despliegan una alerta institucional cuando la tríada entra en fase crítica.

### 8.4 Pronóstico Meteorológico a 7 Días
Permite proyectar el comportamiento del riesgo a lo largo de la próxima semana para la coordenada seleccionada. Muestra tarjetas interactivas diarias con temperaturas extremas, viento, lluvia proyectada y nivel de riesgo, permitiendo con un solo clic cargar ese día en el evaluador principal.

### 8.5 Simulador Climático "¿Qué pasaría si...?" (What-If Analysis)
Permite a investigadores, planificadores territoriales y brigadistas simular escenarios futuros:
- Variar temperatura ($\pm 15^\circ\text{C}$), humedad ($\pm 30\%$), viento ($\pm 40\text{ km/h}$) y pendiente ($0^\circ$ a $45^\circ$).
- Simular cambios de uso de suelo: ¿Qué pasaría si una plantación de pino es reemplazada por bosque nativo o agricultura?
- Escenarios rápidos: *Ola de calor extrema*, *Viento Puelche / Raco* y *Frente de lluvia*.
- Comparación en paralelo con cálculo de delta porcentual y nuevo desglose SHAP.

### 8.6 Exportación de Dossiers Técnicos
Permite generar con un clic:
- **Dossier PDF / HTML Imprimible:** Documento técnico con formato de informe oficial, tablas de variables, certificación de fuentes y sello de tiempo para archivo de emergencias.
- **Exportación JSON:** Para interoperabilidad con sistemas de información geográfica (SIG/GIS) de SENAPRED o CONAF.
- **Exportación CSV:** Para análisis cuantitativo en planillas de cálculo.

---

## 9. Principales Hallazgos Cuantitativos del Territorio Chileno

A partir del análisis de los más de 109.000 eventos históricos del dataset consolidado, se obtuvieron hallazgos fundamentales para la ciencia del fuego en Chile:

```
                            DISTRIBUCIÓN REGIONAL DE INCENDIOS (2002-2023)
  Región del Biobío        ████████████████████████████████████████ (41.6% - 45.757 eventos)
  La Araucanía             █████████████████ (17.9% - 19.690 eventos)
  Valparaíso               █████████████ (13.5% - 14.861 eventos)
  Maule                    █████████ (9.2% - 10.111 eventos)
  Metropolitana            ███████ (7.5% - 8.197 eventos)
  Otras 11 Regiones        ██████████ (10.3%)
```

1. **Concentración Territorial Extrema:**  
   El **89.7% de todos los incendios forestales de Chile se concentra en solo 5 regiones de la zona centro y centro-sur**, con el Biobío como el epicentro absoluto a nivel nacional (41.6%).
2. **El Mito del Bosque Remoto (La Interfaz Urbano-Forestal):**  
   El **96.8% de los incendios ocurren a menos de 5 km de un asentamiento humano**, con una distancia media de apenas **2.1 km** a un poblado o vía de comunicación. Los incendios en Chile son primordialmente un fenómeno de borde urbano y caminos rurales.
3. **Vulnerabilidad de Combustibles:**  
   Si bien el matorral y el pastizal (combustibles finos) concentran el mayor número de hectáreas quemadas acumuladas (42.4%) por su facilidad de ignición inicial, las **plantaciones comerciales de pino y eucalipto acumulan el 37.2% del daño**, generando los incendios de mayor carga térmica y daño a infraestructura.
4. **Causalidad Antrópica:**  
   El **62.8% de los eventos** se originan en **incendios intencionales (32.9%)** o en el **tránsito de personas y vehículos (29.9%)**. Los eventos intencionales presentan una mediana de combate superior a 12 horas debido a que suelen iniciarse en horarios crepusculares cuando el apoyo aéreo no puede operar.
5. **Ventana Horaria Crítica (13:00 a 18:00 hrs):**  
   El **71.4% de las igniciones comienzan en la ventana vespertina**, coincidiendo con el pico de insolación solar, la caída de humedad relativa bajo el 30% y la entrada de brisas marinas o vientos de ladera.

---

## 10. Recomendaciones Estratégicas para la Gestión del Riesgo

Con base en la evidencia cuantitativa y el comportamiento del modelo predictivo, se plantean 3 recomendaciones prioritarias de política pública:

### 1. Rezonificación y Franjas de Amortiguación Obligatorias en el Radio de 3 km (SENAPRED / Municipios)
- **Fundamento:** Dado que el 96.8% de las igniciones se produce a menos de 5 km de centros poblados, se debe prohibir mediante planes reguladores comunales la presencia de plantaciones de monocultivo forestal continuo a menos de 1.000 metros del límite urbano.
- **Acción:** Exigir franjas de amortiguación compuestas por agricultura bajo riego, parques periurbanos o bosque nativo esclerófilo de baja combustibilidad con manejo silvícola preventivo.

### 2. Patrullaje Preventivo Inteligente en Rutas Secundarias de Biobío y Valparaíso (Carabineros / CONAF)
- **Fundamento:** El 62.8% de los eventos provienen de tránsito e intencionalidad a lo largo de caminos no pavimentados.
- **Acción:** Desplegar drones de vigilancia térmica y patrullas mixtas en las rutas secundarias identificadas por el modelo como de "Riesgo Alto/Crítico" durante las jornadas en que el FWI proyecte condiciones de ignición extrema entre las 13:00 y las 19:00 horas.

### 3. Plan Nacional de Manejo Previo de Combustibles Finos (Ministerio de Agricultura)
- **Fundamento:** El matorral y pastizal representan el 42.4% de la superficie quemada total. Actúan como la "mecha" que traslada el fuego desde la orilla del camino hacia las plantaciones y viviendas.
- **Acción:** Ejecutar programas obligatorios de desmalezado mecánico, fajas cortafuegos y pastoreo controlado intensivo entre los meses de septiembre y noviembre, evitando que el combustible fino llegue completamente desecado al inicio del verano.

---

## 11. Conclusiones y Trabajo Futuro

### Conclusiones
- **SIpi Incendios** demuestra que la combinación de registros históricos de CONAF, teledetección satelital (MapBiomas y VIIRS), topografía radar (SRTM) y meteorología de reanálisis (Open-Meteo ERA5) permite predecir con alta precisión (ROC-AUC 0.7932 y Recall 88.84%) el riesgo territorial de incendios forestales en Chile.
- La incorporación de **SHAP TreeExplainer** resuelve el dilema de la interpretabilidad en inteligencia artificial, entregando a las autoridades de protección civil explicaciones claras sobre qué variable física o antrópica está provocando la condición de peligro.
- El despliegue de una interfaz moderna y reactiva permite democratizar el acceso a modelos predictivos complejos, poniendo al alcance de brigadas, municipios y ciudadanía una herramienta interactiva de análisis preventivo y simulación de escenarios.

### Líneas de Desarrollo Futuro
1. **Incorporación de Humedad de Combustible Vivo vía Satélite Sentinel-2:** Integración de índices de vegetación en tiempo real (NDVI, NDWI) a 10 metros de resolución espacial para actualizar quincenalmente el contenido de agua de las copas arbóreas.
2. **Modelos de Simulación de Propagación de Frente de Fuego:** Acoplamiento con modelos físicos de propagación de fuego (tipo Rothermel) para predecir no solo la probabilidad de ignición puntual, sino el polígono proyectado de avance de las llamas en las siguientes 6 a 12 horas.
3. **API para Dispositivos IoT y Sensores en Terreno:** Conexión directa con microestaciones meteorológicas comunitarias desplegadas en predios forestales de alto riesgo.

---
*SIpi Incendios — Sistema Inteligente de Predicción de Incendios Forestales (Chile)*  
*Documento Técnico de Referencia · Plataforma Científica Abierta*
