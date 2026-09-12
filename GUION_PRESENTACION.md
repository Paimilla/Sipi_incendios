# 🎙️ Guion Oficial de Presentación — SIpi Incendios
### *Sistema Inteligente de Predicción y Simulación de Incendios Forestales (Chile Continental)*

> **⏱️ Tiempo estimado:** 8 a 10 minutos  
> **👥 Integrantes:** Tú (Presentador 1) & Tu Compañera (Presentadora 2)

---

## 📋 Resumen del Cronograma

| Bloque | Tema | Responsable |
| :--- | :--- | :--- |
| **1. Introducción** | Problema en Chile, objetivo del proyecto y visión general | **Tú (Presentador 1)** |
| **2. Datos e Integración** | Las 5 bases de datos, muestreo inteligente y pipeline ETL | **Tu Compañera (Presentadora 2)** |
| **3. Modelo y ML** | Feature Engineering, XGBoost V2, Optuna y Validación Temporal | **Tú (Presentador 1)** |
| **4. Demo del Dashboard** | Mapa Leaflet, Tacómetro de Riesgo, Pronóstico 7d, Simulador y SHAP | **Ambos en vivo** |
| **5. Códigos Clave** | Los 5 snippets técnicos comentados línea por línea | **Ambos según diapositiva** |
| **6. Cierre y Preguntas** | Conclusiones y respuestas a preguntas de los profesores | **Ambos** |

---

## 🗣️ BLOQUE 1: Introducción y Contexto
**Responsable:** Tú (Presentador 1)  
**Diapositiva:** *Portada y Planteamiento del Problema*

> *"Buenos días/tardes a la comisión y a todos los presentes. Hoy les vamos a presentar **SIpi Incendios**, un Sistema Inteligente de Predicción y Simulación de Riesgo de Incendios Forestales para Chile Continental.*
>
> *En los últimos años, Chile ha enfrentado temporadas de incendios devastadoras con enormes costos ecológicos, económicos y humanos. Los métodos tradicionales muchas veces se limitan a alertas meteorológicas genéricas o índices estáticos que no consideran la combinación crítica entre el clima, la topografía de nuestras laderas, el tipo de vegetación real y la cercanía a los asentamientos humanos.*
>
> *Nuestra meta con este proyecto fue construir una plataforma integral que no solo prediga con alta precisión la probabilidad de ignición y propagación, sino que además explique **por qué** ocurre el riesgo y permita a las autoridades simular escenarios climáticos antes de que ocurra una catástrofe.*
>
> *Para que un modelo de Machine Learning funcione en un problema tan complejo, el primer gran desafío fue construir un dataset geoespacial multidimensional. A continuación, mi compañera les explicará en detalle qué fuentes de datos utilizamos y cómo logramos unificarlas."*

---

## 🛰️ BLOQUE 2: Fuentes de Datos y Estrategia de Unión ETL
**Responsable:** Tu Compañera (Presentadora 2)  
**Diapositiva:** *Pipeline de Datos Geoespacial / Arquitectura ETL*

> *"Muchas gracias. Para entrenar nuestro sistema necesitábamos cruzar la historia real de incendios con múltiples fuentes satelitales, climáticas y territoriales. El desafío principal fue que **ninguna de estas bases venía junta**: provenían de formatos distintos como CSVs históricos, APIs REST en tiempo real, archivos raster GeoTIFF y bases de datos geográficas.*
>
> *Ocupamos principalmente **6 fuentes de datos clave**:*
>
> 1. ***Registros Históricos Oficiales de Incendios (CONAF / Itrend, 1985–2023):***  
>    *Obtuvimos los registros oficiales de incendios forestales de Chile. Procesamos y limpiamos cientos de archivos CSV anuales con delimitador `|`, filtrando exclusivamente coordenadas válidas dentro del territorio continental chileno para obtener la fecha y ubicación exacta de cada evento (109.985 registros).*
>
> 2. ***Detecciones Térmicas Satelitales (NASA FIRMS — Sensor VIIRS Suomi-NPP 2017–2024):***  
>    *Descargamos y procesamos los archivos anuales globales de la NASA para extraer las anomalías térmicas infrarrojas orbitales en Chile, permitiendo contrastar y validar los reportes de brigadas terrestres con detecciones satelitales directas desde el espacio.*
>
> 3. ***API Meteorológica Histórica y de Pronóstico (Open-Meteo):***  
>    *Para cada punto y fecha, extrajimos una **ventana climática acumulada de los 7 días previos**. No miramos solo el día del evento, sino el estrés hídrico previo: temperatura máxima y media, humedad relativa mínima, viento máximo, precipitación acumulada de 7 días, y variables biofísicas clave como la temperatura y humedad volumétrica del suelo.*
>
> 4. ***Cobertura y Uso de Suelo (MapBiomas Chile 2022):***  
>    *Utilizamos un raster satelital GeoTIFF de 30 metros de resolución espacial. Mediante la librería `rasterio`, realizamos un muestreo espacial directo para identificar qué tipo de combustible vegetal había en cada coordenada (por ejemplo: plantaciones de pino o eucalipto, bosque nativo, matorrales o pastizales).*
>
> 5. ***Modelo de Elevación Digital (NASA SRTM):***  
>    *A través de los datos de la misión de radar SRTM de la NASA, calculamos la elevación en metros, pero además implementamos un algoritmo de gradientes por diferencias finitas en una cuadrícula de 30 metros para derivar la **pendiente del terreno (slope)** y la **orientación de la ladera (aspect)**, ya que el fuego sube más rápido por laderas empinadas y secas.*
>
> 6. ***Asentamientos Humanos (GeoNames Chile):***  
>    *El 99% de los incendios en Chile tienen causa humana. Descargamos el catastro nacional de poblados y ciudades, y mediante un algoritmo de árbol de búsqueda esférica (`BallTree` con métrica Haversine), calculamos la distancia exacta en kilómetros desde cada coordenada hasta el centro poblado más cercano.*
>
> *¿Cómo juntamos todo esto en una sola tabla de entrenamiento?*  
> *Creamos un pipeline ETL automatizado en Python dividido en tres etapas:*
>
> * **a) Muestreo Equilibrado y Negativos Inteligentes:**  
>   *Tomamos 4.500 casos reales de incendios (etiqueta 1). Para los casos negativos (etiqueta 0 o días sin incendio), generamos muestras en las mismas ubicaciones pero con fechas aleatorias. Además, aplicamos **Smart Negative Sampling**: descartamos negativos en zonas donde es físicamente imposible que haya un incendio forestal (como cuerpos de agua o glaciares), garantizando que el modelo aprenda sobre vegetación realmente combustible.*
> * **b) Cruce Temporal y Clima Vía Multithreading:**  
>   *A través de llamadas concurrentes a la API climática, sincronizamos cada evento con su historial meteorológico de 7 días previos.*
> * **c) Cruce Espacial Multidimensional:**  
>   *Pegamos a cada fila su uso de suelo de MapBiomas, su distancia al poblado más cercano de GeoNames y su topografía calculada con NASA SRTM.*
>
> *El resultado final fue un dataset maestro consolidado con **22 variables predictivas** listas para alimentar el modelo de Machine Learning que les presentará mi compañero."*

---

## 🤖 BLOQUE 3: Ingeniería de Variables, Modelo y Validación
**Responsable:** Tú (Presentador 1)  
**Diapositiva:** *Feature Engineering, XGBoost V2 y Validación Temporal*

> *"A partir del dataset consolidado, realizamos **Ingeniería de Variables** para capturar fenómenos físicos no lineales:*
> - *Agregamos componentes cíclicos para la estacionalidad (`month_sin`, `month_cos`).*
> - *Creamos índices combinados: el **Índice de Sequedad**, el **Ratio Temperatura/Humedad** y el **Índice Meteorológico de Fuego (FWI)**, que combina calor, viento y sequedad.*
>
> *Para el modelamiento seleccionamos **XGBoost V2 (eXtreme Gradient Boosting)** por su alta capacidad para manejar relaciones no lineales y datos tabulares geoespaciales. Optimizamos sus hiperparámetros utilizando **Optuna con 80 trials** y validación cruzada estratificada.*
>
> *Un aspecto metodológico crítico que implementamos fue la **Validación Temporal Estricta (Temporal Split)**:*
> - *Entrenamos el modelo con datos de **2002 a 2018** (más de 5.800 muestras).*
> - *Lo evaluamos con datos de **2019 a 2020** (casi 1.000 muestras que el modelo jamás vio en el tuning). Esto evita cualquier fuga de datos (Data Leakage) y simula el rendimiento del modelo en un entorno operativo real.*
>
> *En los datos de prueba futuros logramos:*
> - *Un **ROC-AUC de 0.7932** y un **PR-AUC de 0.7975**.*
> - *Un **F1-Score de 0.7515**.*
> - *Y lo más importante para la gestión de emergencias: un **Recall del 88.84%** en la detección de incendios reales, minimizando los falsos negativos."*

---

## 🌐 BLOQUE 4: Demostración de la Plataforma Web y SHAP
**Responsable:** Ambos *(uno maneja la interfaz y el otro comenta)*  
**Pantalla:** *Demostración en vivo en `http://localhost:5000`*

> *"Para que este modelo no se quedara solo en un notebook, desarrollamos una plataforma web interactiva en Flask con diseño moderno (Glassmorphism) dividida en 4 módulos:*
>
> 1. ***Predicción Puntual y Mapa Geoespacial:**  
>    *Al hacer clic en cualquier punto de Chile continental, el servidor consulta automáticamente las capas de MapBiomas, SRTM, GeoNames y el clima en tiempo real. Un tacómetro dinámico nos indica el nivel de riesgo (**Bajo, Moderado, Alto o Crítico**).*
>
> 2. ***Explicabilidad en Vivo con SHAP (SHapley Additive exPlanations):**  
>    *(Mostrar gráfico de barras/waterfall SHAP en la pantalla)*  
>    *El modelo no es una caja negra: calculamos en milisegundos qué variables específicas están empujando el riesgo al alza (por ejemplo, temperaturas sobre 32°C y vientos fuertes) o a la baja (como alta humedad o cercanía a pastos húmedos).*
>
> 3. ***Pronóstico de Riesgo a 7 Días:**  
>    *Conectamos el pronóstico horario de Open-Meteo para calcular la curva de riesgo proyectada para la semana entrante, permitiendo anticipar patrullajes preventivos.*
>
> 4. ***Simulador "¿Qué pasaría si...?" (What-If Simulator):**  
>    *Permite a un analista mover sliders de temperatura, humedad, viento o pendiente, o activar escenarios rápidos como 'Ola de calor extrema' o 'Viento Puelche', observando inmediatamente cómo cambia la probabilidad de incendio."*

---

## 💻 BLOQUE 5: Fragmentos de Código Comentados Línea por Línea

### 1. Cálculo Físico de Topografía (NASA SRTM)
```python
# 1. dz_dx: Gradiente en el eje Este-Oeste (X) a 30 metros de distancia
dz_dx = (elev_e - elev_w) / (2.0 * d_lon_m)

# 2. dz_dy: Gradiente en el eje Norte-Sur (Y) a 30 metros de distancia
dz_dy = (elev_n - elev_s) / (2.0 * d_lat_m)

# 3. slope_rad: Magnitud del gradiente convertida a ángulo mediante arcotangente
slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))

# 4. slope_deg: Convierte a grados de inclinación (0° = plano, 45° = muy empinado)
slope_deg = math.degrees(slope_rad)

# 5. aspect_rad: Dirección de máxima pendiente en radianes usando atan2
aspect_rad = math.atan2(dz_dx, dz_dy)

# 6. aspect_deg: Convierte a grados de brújula [0°-360°] (0°=N, 90°=E, 180°=S, 270°=W)
aspect_deg = (math.degrees(aspect_rad) + 360) % 360
```

### 2. Distancia a Poblados con Árboles Espaciales (`BallTree`)
```python
# 1. Convierte coordenadas de latitud/longitud de los 6.967 poblados a radianes
places_rad = np.radians(np.vstack([places['latitude'], places['longitude']]).T)

# 2. Construye un BallTree con métrica Haversine para cálculo esférico exacto
tree = BallTree(places_rad, metric='haversine')

# 3. Convierte coordenadas de los incendios a radianes
fire_rad = np.radians(np.vstack([df['Latitud'], df['Longitud']]).T)

# 4. Busca el vecino más cercano (k=1) en tiempo logarítmico O(log N)
distances, _ = tree.query(fire_rad, k=1)

# 5. Multiplica por el radio terrestre (6.371 km) para obtener km físicos reales
df['dist_nearest_town_km'] = distances.flatten() * 6371.0
```

### 3. Ingeniería de Variables Físicas (Feature Engineering)
```python
# 1. Índice de Sequedad: multiplica temperatura máxima por el déficit de humedad
df['dryness_index'] = df['temp_max_window'] * (100 - df['humidity_mean_window']) / 100

# 2. Ratio Temp/Humedad: mide evaporación extrema (+1 evita división por cero)
df['temp_humidity_ratio'] = df['temp_max_window'] / (df['humidity_min_window'] + 1)

# 3. Índice FWI Compuesto: combina calor, ráfagas de viento y sequedad de combustible
df['fire_weather_index'] = (df['temp_max_window'] * df['wind_speed_max_window'] 
                            / (df['humidity_min_window'] + 1))
```

### 4. División Temporal y Optuna (Sin Data Leakage)
```python
# 1. train_mask: Filtra como entrenamiento únicamente registros pasados (2002 a 2018)
train_mask = df['year'] < 2019

# 2. test_mask: Reserva exclusivamente los años futuros (2019 a 2020) para evaluación
test_mask  = (df['year'] >= 2019) & (df['year'] <= 2020)

# 3. Separa variables y etiquetas de entrenamiento y prueba
X_train, y_train = df.loc[train_mask, features], df.loc[train_mask, 'Fire_Probability']
X_test,  y_test  = df.loc[test_mask,  features], df.loc[test_mask,  'Fire_Probability']

# 4. Optimización bayesiana con Optuna en 80 trials maximizando ROC-AUC
study = optuna.create_study(direction='maximize')
study.optimize(lambda trial: objective(trial, X_train, y_train, w_train), n_trials=80)
```

### 5. Explicabilidad Local en Vivo con SHAP
```python
# 1. Inicializa el explicador analítico de árboles basado en teoría de juegos de Shapley
SHAP_EXPLAINER = shap.TreeExplainer(MODEL)

# 2. En cada predicción web, calcula el impacto marginal de las 22 variables
shap_values = SHAP_EXPLAINER(df_sample)
# 3. Separa factores que aumentan el riesgo (+) de los que lo disminuyen (-)
```

---

## 🏁 BLOQUE 6: Conclusiones y Cierre
**Responsables:** Ambos

> **Tu Compañera:**  
> *"Como conclusión, demostramos que la integración de datos multidisciplinarios —satelitales, meteorológicos, topográficos y humanos— supera ampliamente los análisis basados únicamente en estaciones meteorológicas aisladas."*
>
> **Tú:**  
> *"El sistema entrega una herramienta operable en tiempo real, transparente gracias a SHAP y capaz de integrarse con sistemas de alerta temprana de CONAF, SENAPRED o municipios forestales.*
>
> *Muchas gracias por su atención. Quedamos a su total disposición para responder cualquier pregunta."*

---

## 🧠 BLOQUE 7: Preguntas Frecuentes de la Comisión (Tarjeta Trampa)

* **P1: ¿Por qué hay tanta variación de riesgo entre dos puntos que están al lado?**  
  *R:* *"Porque evaluamos a 30 metros de resolución. Aunque el clima sea igual, el uso de suelo puede cambiar de un campo agrícola plano (sin riesgo de propagación) a una zona de interfaz urbano-forestal con pendiente activa, donde se concentra la ignición antrópica y el efecto ladera."*

* **P2: ¿De verdad Open-Meteo consulta el clima para cada punto que toco?**  
  *R:* *"Sí. Cada clic envía las coordenadas exactas a la API de Open-Meteo, extrayendo la ventana histórica y de pronóstico de 7 días. Además, contamos con una caché en memoria de 30 minutos para responder en 0 milisegundos en puntos repetidos y ahorrar cuota."*

* **P3: ¿Por qué usaron Temporal Split y no K-Fold aleatorio?**  
  *R:* *"Porque el clima y los incendios tienen fuerte autocorrelación temporal. Un split aleatorio filtraría información del mismo verano (data leakage), inflando artificialmente las métricas. El split temporal prueba la capacidad real del modelo de predecir temporadas futuras."*
