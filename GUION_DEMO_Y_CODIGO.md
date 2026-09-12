# 🎙️ Guion Oficial de Exposición: SIpi Incendios
### *Cierre de Diapositivas, Demostración en Vivo y Recorrido por el Código Fuente*

> **⏱️ Tiempo estimado:** 6 a 7 minutos (desde la conclusión de diapositivas hasta las preguntas)  
> **👥 Tono:** Cercano, dinámico y natural (exposición de curso universitario), con rigor técnico y dominio del código.

---

## 📋 Resumen del Cronograma de este Bloque

| Bloque | Contenido | Soporte en Pantalla | Tiempo |
| :--- | :--- | :--- | :--- |
| **Bloque 1** | Síntesis, Políticas Públicas y Limitaciones (Diapositivas 12 a 14) | Presentación (Diapositivas) | ~1 min 25s |
| **Bloque 2** | Demostración en Vivo de la Plataforma Web (Pasos A, B, C y D) | Navegador (`localhost:5000`) | ~2 min 30s |
| **Bloque 3** | Recorrido por el Código Fuente (Backend, SRTM, BallTree y Split Temporal) | VS Code (Editor) | ~2 min 00s |
| **Bloque 4** | Cierre Relajado y Ronda de Preguntas | Navegador / Mapa interactivo | ~30s |

---

## 🗣️ BLOQUE 1: Cierre de Diapositivas (04:35 – 06:00)
`[En pantalla: Proyección de las diapositivas de la presentación]`

### Diapositiva 12: Síntesis y Conclusiones (04:35 – 05:05 · 30s)
* **Texto en lámina:** Resumen de las 5 conclusiones (Territorio, Combustible, Régimen no lineal, Intencionalidad, Interfaz urbana).
* **Pauta escénica:** Enunciación clara, tipo viñeta verbal estructurada.
* **Guion verbal:**
> *"En síntesis, este diagnóstico nos deja cinco certezas científicas:*  
> *Primero, el epicentro estructural es el Biobío y la zona centro-sur.*  
> *Segundo, los matorrales facilitan el inicio, pero las plantaciones comerciales magnifican el daño.*  
> *Tercero, el régimen de daño depende de eventos meteorológicos extremos y no de la simple cantidad de focos.*  
> *Cuarto, más de 6 de cada 10 fuegos son provocados por intencionalidad o tránsito en caminos.*  
> *Y quinto, el combate se decide en la interfaz humano-forestal."*

---

### Diapositiva 13: Recomendaciones de Política Pública (05:05 – 05:35 · 30s)
* **Texto en lámina:** Fajas de 1.000m en SENAPRED, patrullaje en rutas secundarias (Carabineros/CONAF) y desmalezado pre-diciembre (Minagri).
* **Pauta escénica:** Voz proactiva, orientada a la toma de decisiones prácticas.
* **Guion verbal:**
> *"La ciencia de datos debe traducirse en acción preventiva. Por eso proponemos tres directrices operativas concretas:*  
> *Para SENAPRED y municipios: ordenar fajas de amortiguación obligatorias de 1.000 metros en torno a todo poblado dentro del radio crítico de 3 kilómetros.*  
> *Para Carabineros y CONAF: concentrar el patrullaje disuasivo y con drones en rutas secundarias de Biobío y Valparaíso durante días de alerta roja.*  
> *Y para el Ministerio de Agricultura: adelantar el desmalezado de combustibles finos al mes de noviembre, antes del secado estival."*

---

### Diapositiva 14: Limitaciones y Paso a la Demo en Vivo (05:35 – 06:00 · 25s)
* **Texto en lámina:** Limitaciones (humedad viva de terreno y subregistro judicial) + Paso a demostración interactiva.
* **Pauta escénica:** Cierre enérgico, agradecimiento de la parte teórica y cambio inmediato de pantalla (`Alt + Tab` al navegador web en el minuto 06:00 exacto).
* **Guion verbal:**
> *"Como limitaciones de este estudio, reconocemos la falta de sensores en terreno para medir la humedad viva de la biomasa y el subregistro judicial de las causas en zonas aisladas.*  
> *Pero no quisimos quedarnos solo en diapositivas ni en un notebook: convertimos todo este análisis en un software real. A continuación, los invitamos a ver en funcionamiento nuestra plataforma interactiva **SIpi Incendios**."*

---

## 🌐 BLOQUE 2: Demostración en Vivo de la Plataforma Web (06:00 – 08:30)
`[En pantalla: Navegador web en http://localhost:5000 mostrando el dashboard interactivo]`

### Paso A: El clic en el mapa y el Tacómetro de Riesgo (06:00 – 06:45)
`[Acción: En la pestaña principal, haz clic en el mapa en una zona forestal del Biobío o Valparaíso]`

> *"Miren, esta es la interfaz principal. Es un mapa interactivo de Chile. Si yo hago clic en cualquier punto del territorio —por ejemplo aquí en la Región del Biobío— miren lo que pasa en menos de un segundo:*  
>  
> *El sistema no inventa nada: por debajo, toma las coordenadas y hace 4 consultas en paralelo:*  
> 1. *Va a la API de Open-Meteo y reconstruye el clima acumulado de los últimos 7 días.*  
> 2. *Va al mapa satelital de MapBiomas y me dice exactamente qué vegetación hay en ese metro cuadrado (aquí detectó plantación forestal).*  
> 3. *Calcula qué tan empinada está la ladera con datos de radar de la NASA.*  
> 4. *Y mide a cuántos kilómetros está el pueblo más cercano.*  
>  
> *Con esas 22 variables, el modelo XGBoost evalúa el riesgo y este **tacómetro dinámico** nos marca la probabilidad. En este caso nos da riesgo Alto o Crítico, y abajo nos da recomendaciones automáticas alineadas con los protocolos de CONAF y SENAPRED."*

---

### Paso B: Explicabilidad con SHAP en Vivo (06:45 – 07:20)
`[Acción: Baja en la barra lateral para mostrar el gráfico de barras rojas y azules de SHAP]`

> *"Una cosa muy bacán que implementamos y que para nosotros era clave: **el modelo no es una caja negra**. No queríamos que solo tirara un porcentaje y ya.*  
>  
> *Integramos **SHAP** en tiempo real. Aquí le explicamos al usuario por qué el modelo tomó esa decisión:*  
> - *Las barras en **rojo** son las variables que empujan el riesgo hacia arriba: por ejemplo, temperaturas sobre 32 grados, ráfagas de viento y sequedad del suelo.*  
> - *Y las barras en **azul** son las cosas que juegan a favor, como si hubiera humedad en el aire o terreno plano.*  
> *Esto permite que si alguien de emergencias usa la app, no solo ve una alerta, sino que entiende la causa física que la provoca."*

---

### Paso C: El Simulador "¿Qué pasaría si...?" (What-If) (07:20 – 08:00)
`[Acción: Clic en la pestaña 'Simulador What-If' y pulsa el botón del preset 'Ola de Calor Extrema' o mueve sliders]`

> *"Esta otra pestaña es el Simulador de Escenarios. Pensamos: ¿qué pasa si un analista de SENAPRED quiere anticiparse antes de que llegue el fin de semana?*  
>  
> *Aquí pusimos controles donde uno puede cambiar los parámetros climáticos, o probar escenarios típicos de Chile. Si yo aprieto **'Ola de calor extrema'**, la temperatura sube a 38 grados, la humedad cae al 15% y entra viento fuerte. Le damos a 'Simular', y miren cómo la probabilidad se dispara inmediatamente a nivel Crítico.*  
> *Esto sirve para jugar con hipótesis y ver qué tan vulnerable es una zona ante eventos meteorológicos extremos."*

---

### Paso D: Pronóstico de Riesgo a 7 Días (08:00 – 08:30)
`[Acción: Clic en la pestaña 'Pronóstico 7 Días' para mostrar la curva semanal]`

> *"Y por último en la web, en esta pestaña conectamos el pronóstico del tiempo para la semana entrante. El sistema calcula el riesgo día por día de aquí al próximo domingo, para que las brigadas puedan planificar patrullajes antes de que empiece el fuego.*  
>  
> *Ahora pasemos a VS Code para mostrarles rápidamente cómo está construido esto por dentro."*

---

## 💻 BLOQUE 3: Recorrido por el Código Fuente en VS Code (08:30 – 10:30)
`[Acción: Cambiar de ventana a VS Code y abrir los archivos correspondientes]`

### 1. Backend Flask y la Física del Fuego (`src/dashboard/server.py`)
`[Acción: Abrir server.py y mostrar el endpoint /api/predict alrededor de la línea 520]`

> *"Para que vean cómo funciona el servidor por detrás, aquí en `server.py` está la función que recibe el clic del mapa:*  
> *Llama a nuestras funciones espaciales: clima, vegetación, pueblo cercano y topografía. Pero fíjense en este detalle de acá:"*

```python
# Restricción física de combustible
if land_cover_class in NON_BURNABLE_CLASSES:
    probability = 0.0000  # En agua, glaciar o roca el riesgo es 0%
else:
    feat_dict = build_feature_dict(lat, lon, fecha, weather, ...)
    df = pd.DataFrame([feat_dict])[FEATURES]
    probability = float(MODEL.predict_proba(df)[:, 1][0])
    shap_factors = explain_prediction(df)
```

> *"Le pusimos **física del fuego**: si alguien hace clic en medio de un lago, en un río o en la nieve de la cordillera, no gastamos tiempo corriendo el modelo: el código sabe que ahí no hay combustible y entrega 0% de probabilidad de inmediato. Si hay vegetación, recién ahí arma el vector con las 22 variables y ejecuta `predict_proba` y SHAP."*

---

### 2. El Cálculo de la Pendiente con NASA SRTM (`src/data/add_topography.py`)
`[Acción: Abrir add_topography.py o la función query_topography]`

> *"Otro detalle técnico importante: ¿cómo sabe el sistema si el cerro es empinado? No usamos solo la altura sobre el nivel del mar, porque un altiplano está a 3.000 metros pero es plano. Lo que importa para el fuego es la **inclinación de la ladera**:"*

```python
# Tomamos 4 puntos vecinos a 30 metros de distancia
dz_dx = (elev_e - elev_w) / (2.0 * d_lon_m)
dz_dy = (elev_n - elev_s) / (2.0 * d_lat_m)

# Con trigonometría derivamos la pendiente exacta en grados
slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
slope_deg = math.degrees(slope_rad)
```

> *"Con diferencias finitas a 30 metros calculamos el ángulo exacto de la ladera en grados. Esto es clave porque el fuego sube mucho más rápido por laderas empinadas debido al calor por convección."*

---

### 3. Búsqueda Espacial Rápida con BallTree (`src/data/add_anthropogenic.py`)
`[Acción: Abrir add_anthropogenic.py]`

> *"Y para saber si hay humanos cerca, usamos la base de GeoNames con casi 7.000 poblados chilenos. Como no podíamos calcular la distancia a los 7.000 puntos en cada clic porque se pegaría la app, usamos un `BallTree` con métrica Haversine:"*

```python
tree = BallTree(places_rad, metric='haversine')
dist, idx = tree.query(coords_rad, k=1)
dist_km = dist * 6371.0
```

> *"Indexamos todo Chile en un árbol esférico. La búsqueda se ejecuta en tiempo logarítmico, demorando menos de 2 milisegundos en decirnos el nombre del pueblo más cercano y su distancia en kilómetros."*

---

### 4. Entrenamiento sin Trampas: Split Temporal (`src/models/train_model_final.py`)
`[Acción: Abrir train_model_final.py]`

> *"Por último, en el entrenamiento aplicamos un principio metodológico clave: **Split Temporal Estricto**:"*

```python
# Evitar Data Leakage: nunca mezclar futuro con pasado
train_mask = df['Temporada'] <= '2017-2018'  # Datos históricos (2002 a 2018)
test_mask = df['Temporada'] >= '2019-2020'   # Datos futuros ciegos (2019 a 2020)

X_train, y_train = X[train_mask], y[train_mask]
X_test, y_test = X[test_mask], y[test_mask]
```

> *"Si usas validación cruzada aleatoria en series de tiempo, el modelo hace trampa porque aprende cosas del futuro. Nosotros entrenamos con datos hasta 2018 y lo testeamos con 2019 y 2020. En esos datos que jamás vio, el modelo logró un **ROC-AUC de 0.79**, un **PR-AUC de 0.80** y un **Recall del 88.8%**, o sea, es capaz de detectar casi 9 de cada 10 incendios reales."*

---

## 🎯 BLOQUE 4: Cierre Relajado y Preguntas (10:30 – 11:00 · 30s)
`[Acción: Volver a poner en pantalla el mapa de la app web]`

> *"En resumen: logramos armar un proyecto completo, que no se quedó solo en un notebook tirando gráficos, sino que toma datos satelitales crudos, topografía de la NASA y clima en tiempo real, y los convierte en una aplicación web interactiva, explicable y lista para usarse.*  
>  
> *Eso es todo por nuestra parte. Quedamos muy atentos por si el profe o algún compañero tiene preguntas o si quieren que probemos alguna coordenada en particular en el mapa. ¡Muchas gracias!"*
