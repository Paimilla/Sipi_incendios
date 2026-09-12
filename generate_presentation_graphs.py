# -*- coding: utf-8 -*-
"""
Generador de Gráficos de Alta Definición para la Presentación SIpi Incendios
Alineado exactamente con las diapositivas de la presentación ejecutiva.
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Configurar estilo global y tipografías
plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'DejaVu Sans']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['axes.edgecolor'] = '#D0D7DE'
plt.rcParams['axes.linewidth'] = 0.8

# Paleta oficial extraída de la presentación
COLOR_PRIMARY = '#BA4A38'     # Terracota / Rojizo distintivo de la presentación
COLOR_SECONDARY = '#1C3F2B'   # Verde bosque profundo
COLOR_ACCENT = '#D97A6C'      # Terracota suave
COLOR_FOREST = '#2D6A4F'      # Verde para vegetación nativa
COLOR_DARK_TEXT = '#2C3E50'   # Carbón oscuro para títulos y textos

BASE_DIR = Path(__file__).resolve().parent
out_dirs = [
    BASE_DIR / "informe_miniproyecto",
    BASE_DIR / "graficos_presentacion"
]
for d in out_dirs:
    d.mkdir(parents=True, exist_ok=True)

# Limpiador de texto para resolver caracteres corruptos en datos crudos de CONAF
def clean_region_name(name):
    if not isinstance(name, str):
        return name
    name_clean = name.replace('\xad', '').replace('\x91', '').replace('', '')
    if 'Biob' in name_clean:
        return 'Biobío'
    if 'Araucan' in name_clean:
        return 'Araucanía'
    if 'Valpara' in name_clean:
        return 'Valparaíso'
    if 'Los R' in name_clean:
        return 'Los Ríos'
    if 'uble' in name_clean:
        return 'Ñuble'
    if 'Ays' in name_clean:
        return 'Aysén'
    if 'Tarapac' in name_clean:
        return 'Tarapacá'
    return name_clean.strip()

def clean_cause_name(c):
    if not isinstance(c, str):
        return c
    c_clean = c.replace('\xad', '').replace('\x91', '').replace('', '')
    if 'intencionales' in c_clean.lower():
        return 'Incendios Intencionales'
    if 'tránsito' in c_clean.lower() or 'veh' in c_clean.lower():
        return 'Tránsito de Personas / Vehículos'
    if 'desconocida' in c_clean.lower():
        return 'Causa Desconocida'
    if 'recreativas' in c_clean.lower():
        return 'Actividades Recreativas'
    if 'agr' in c_clean.lower():
        return 'Faenas Agrícolas y Pecuarias'
    if 'forestales' in c_clean.lower() and 'faenas' in c_clean.lower():
        return 'Faenas Forestales'
    if 'desechos' in c_clean.lower():
        return 'Quema de Desechos'
    if 'eléctricos' in c_clean.lower() or 'electricos' in c_clean.lower():
        return 'Accidentes Eléctricos'
    if 'naturales' in c_clean.lower():
        return 'Incendios Naturales'
    return c_clean.strip()

# Carga de datos
csv_path = BASE_DIR / "data" / "processed" / "itrend_incendios_historicos.csv"
df_fires = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
df_fires.columns = [c.strip() for c in df_fires.columns]
df_fires['Región'] = df_fires['Región'].apply(clean_region_name)
df_fires['Causa'] = df_fires['Causa'].apply(clean_cause_name)
df_fires['Superficie quemada total [ha]'] = pd.to_numeric(df_fires['Superficie quemada total [ha]'], errors='coerce').fillna(0)
df_fires['Duración (minutos)'] = pd.to_numeric(df_fires['Duración (minutos)'], errors='coerce').fillna(0)
df_fires['Duracion_Horas'] = df_fires['Duración (minutos)'] / 60.0

total_incendios = len(df_fires)
print(f"Dataset cargado y sanitizado: {total_incendios:,} registros.")

def save_plot(fig, filename):
    for d in out_dirs:
        filepath = d / filename
        fig.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    print(f"[OK] Guardado: {filename}")
    plt.close(fig)

# ==============================================================================
# GRÁFICO 1: DISTRIBUCIÓN REGIONAL (Diapositiva 5)
# ==============================================================================
print("\nGenerando Gráfico 1: Distribución Regional...")
reg_counts = df_fires['Región'].value_counts().head(10).sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(10, 6.2), facecolor='#FFFFFF')
ax.set_facecolor('#FFFFFF')

bar_colors = []
for r in reg_counts.index:
    if r == 'Biobío':
        bar_colors.append(COLOR_PRIMARY)
    elif r in ['Araucanía', 'Valparaíso', 'Maule', 'Metropolitana']:
        bar_colors.append('#C86B58')
    else:
        bar_colors.append('#9EAAB1')

bars = ax.barh(reg_counts.index, reg_counts.values, color=bar_colors, height=0.68, edgecolor='none')

for bar in bars:
    w = bar.get_width()
    pct = (w / total_incendios) * 100
    y_pos = bar.get_y() + bar.get_height() / 2
    if w > 30000:
        ax.text(w + 700, y_pos, f"{int(w):,} ({pct:.1f}%)", va='center', fontsize=11, fontweight='bold', color=COLOR_PRIMARY)
    elif w > 10000:
        ax.text(w + 700, y_pos, f"{int(w):,} ({pct:.1f}%)", va='center', fontsize=10, fontweight='bold', color='#2C3E50')
    else:
        ax.text(w + 700, y_pos, f"{int(w):,} ({pct:.1f}%)", va='center', fontsize=9.5, color='#4A5568')

ax.set_title('Top 10 Regiones con Mayor Frecuencia de Incendios Forestales', fontsize=14, fontweight='bold', pad=18, color=COLOR_DARK_TEXT, loc='left')
ax.set_xlabel('Número Total de Incendios Registrados (2002–2020)', fontsize=11, fontweight='semibold', color=COLOR_DARK_TEXT, labelpad=10)
ax.set_xlim(0, 55000)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{int(x):,}"))
ax.grid(axis='x', linestyle='--', alpha=0.35, color='#D0D7DE')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#D0D7DE')
ax.spines['bottom'].set_color('#D0D7DE')
ax.tick_params(axis='y', labelsize=11, labelcolor=COLOR_DARK_TEXT)
ax.tick_params(axis='x', labelsize=10, labelcolor='#555555')

ax.text(0.98, 0.12, 'Zona Centro-Sur (Top 5):\nConcentra el 89.7% del total nacional',
        transform=ax.transAxes, fontsize=10.5, fontweight='bold', color=COLOR_SECONDARY,
        ha='right', va='bottom', bbox=dict(boxstyle='round,pad=0.6', facecolor='#F4F6F4', edgecolor='#B8D0C2', alpha=0.92))

save_plot(fig, 'grafico_1_distribucion_regional.png')

# ==============================================================================
# GRÁFICO 2: COBERTURA VEGETAL (Diapositiva 6)
# ==============================================================================
print("\nGenerando Gráfico 2: Superficie Quemada por Cobertura...")
veg_data = {
    'Plantaciones de Pino': (df_fires['Superficie quemada: Pino A [ha]'].sum() +
                             df_fires['Superficie quemada: Pino B [ha]'].sum() +
                             df_fires['Superficie quemada: Pino C [ha]'].sum()),
    'Matorral': df_fires['Superficie quemada: Matorral [ha]'].sum(),
    'Pastizales': df_fires['Superficie quemada: Pastizal [ha]'].sum(),
    'Arbolado Nativo': df_fires['Superficie quemada: Arbolado [ha]'].sum(),
    'Plantaciones de Eucalipto': df_fires['Superficie quemada: Eucalípto [ha]'].sum(),
    'Uso Agrícola y Otros': (df_fires['Superficie quemada: Agrícola [ha]'].sum() +
                             df_fires['Superficie quemada: Otras plantas [ha]'].sum())
}
veg_s = pd.Series(veg_data).sort_values(ascending=True)
total_ha_ref = 1471366.0

fig, ax = plt.subplots(figsize=(10.5, 6.2), facecolor='#FFFFFF')
ax.set_facecolor('#FFFFFF')

veg_colors = []
for k in veg_s.index:
    if 'Pino' in k:
        veg_colors.append('#BA4A38')      # Terracota corporativo (Pino)
    elif 'Eucalipto' in k:
        veg_colors.append('#D67A53')      # Ámbar cálido (Eucalipto)
    elif 'Matorral' in k:
        veg_colors.append('#2D6A4F')      # Verde bosque (Matorral)
    elif 'Pastizales' in k:
        veg_colors.append('#40916C')      # Verde medio (Pastizales)
    elif 'Nativo' in k:
        veg_colors.append('#52B788')      # Verde esmeralda (Arbolado nativo)
    else:
        veg_colors.append('#95A5A6')

bars = ax.barh(veg_s.index, veg_s.values / 1000, color=veg_colors, height=0.65, edgecolor='none')

for bar in bars:
    w = bar.get_width()
    pct = (w * 1000 / total_ha_ref) * 100
    ax.text(w + 7, bar.get_y() + bar.get_height()/2, f"{w:,.1f}k ha  ({pct:.1f}%)",
            va='center', fontsize=10.5, fontweight='bold', color=COLOR_DARK_TEXT)

ax.set_title('Superficie Total Afectada según Tipo de Cobertura Vegetal', fontsize=14, fontweight='bold', pad=18, color=COLOR_DARK_TEXT, loc='left')
ax.set_xlabel('Miles de Hectáreas Quemadas (k ha)', fontsize=11, fontweight='semibold', color=COLOR_DARK_TEXT, labelpad=10)
ax.set_xlim(0, 480)
ax.grid(axis='x', linestyle='--', alpha=0.35, color='#D0D7DE')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#D0D7DE')
ax.spines['bottom'].set_color('#D0D7DE')
ax.tick_params(axis='y', labelsize=11, labelcolor=COLOR_DARK_TEXT)
ax.tick_params(axis='x', labelsize=10, labelcolor='#555555')

plantaciones_ha = veg_data['Plantaciones de Pino'] + veg_data['Plantaciones de Eucalipto']
plantaciones_pct = (plantaciones_ha / total_ha_ref) * 100
finos_ha = veg_data['Matorral'] + veg_data['Pastizales']
finos_pct = (finos_ha / total_ha_ref) * 100

summary_text = (
    f"• Plantaciones Comerciales (Pino + Eucalipto): {plantaciones_pct:.1f}% ({plantaciones_ha/1000:,.0f}k ha)\n"
    f"• Combustibles Finos de Inicio (Matorral + Pasto): {finos_pct:.1f}% ({finos_ha/1000:,.0f}k ha)\n"
    f"• Arbolado Nativo Afectado: 16.8% (247k ha)"
)
ax.text(0.98, 0.12, summary_text,
        transform=ax.transAxes, fontsize=10, fontweight='medium', color='#2C3E50',
        ha='right', va='bottom', bbox=dict(boxstyle='round,pad=0.7', facecolor='#FDF7F4', edgecolor='#E6BCB2', alpha=0.95))

save_plot(fig, 'grafico_2_cobertura_quemada.png')

# ==============================================================================
# GRÁFICO 3: EVOLUCIÓN TEMPORAL (Diapositiva 7)
# ==============================================================================
print("\nGenerando Gráfico 3: Evolución Temporal Interanual...")
temp_stats = df_fires.groupby('Temporada')['Superficie quemada total [ha]'].agg(['count', 'sum']).reset_index()
temp_stats = temp_stats[temp_stats['count'] > 100].sort_values('Temporada')

fig, ax1 = plt.subplots(figsize=(11.5, 6.0), facecolor='#FFFFFF')
ax1.set_facecolor('#FFFFFF')

x_indices = np.arange(len(temp_stats))
temporadas = temp_stats['Temporada'].tolist()
ha_miles = temp_stats['sum'].values / 1000
counts = temp_stats['count'].values

bar_palette = [COLOR_PRIMARY if '2016-2017' in t else '#E5AEA4' for t in temporadas]
bars = ax1.bar(x_indices, ha_miles, color=bar_palette, width=0.58, label='Superficie Quemada (Miles de ha)', edgecolor='none')

ax1.set_ylabel('Superficie Quemada (Miles de ha)', color=COLOR_PRIMARY, fontsize=11, fontweight='bold')
ax1.tick_params(axis='y', labelcolor=COLOR_PRIMARY, labelsize=10)
ax1.set_ylim(0, 680)

ax2 = ax1.twinx()
line = ax2.plot(x_indices, counts, color='#1A365D', lw=2.6, marker='o', markersize=5.5, label='Frecuencia de Incendios')
ax2.set_ylabel('Frecuencia Anual de Incendios', color='#1A365D', fontsize=11, fontweight='bold')
ax2.tick_params(axis='y', labelcolor='#1A365D', labelsize=10)
ax2.set_ylim(0, 10500)
ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{int(x):,}"))

ax1.set_xticks(x_indices)
ax1.set_xticklabels(temporadas, rotation=45, ha='right', fontsize=9.5, color=COLOR_DARK_TEXT)
ax1.set_xlabel('Temporada Operativa Oficial', fontsize=11, fontweight='semibold', color=COLOR_DARK_TEXT, labelpad=8)

idx_2016 = temporadas.index('2016-2017')
ax1.annotate('Tormenta de Fuego 2017\n570.160 ha (Récord histórico)',
             xy=(idx_2016, 570.16),
             xytext=(idx_2016 - 3.8, 595),
             arrowprops=dict(facecolor=COLOR_PRIMARY, edgecolor=COLOR_PRIMARY, arrowstyle='->', lw=1.8, shrinkB=6),
             bbox=dict(boxstyle='round,pad=0.55', facecolor='#FDF2F0', edgecolor=COLOR_PRIMARY, lw=1.2),
             fontweight='bold', fontsize=10, color=COLOR_PRIMARY)

ax1.set_title('Evolución Temporal: Frecuencia Anual vs. Superficie Devastada (2002–2020)', fontsize=13.5, fontweight='bold', pad=18, color=COLOR_DARK_TEXT, loc='left')
ax1.grid(axis='x', linestyle=':', alpha=0.3, color='#D0D7DE')
ax1.spines['top'].set_visible(False)
ax2.spines['top'].set_visible(False)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', frameon=True, facecolor='#FFFFFF', edgecolor='#D0D7DE', fontsize=9.5)

save_plot(fig, 'grafico_3_evolucion_temporal.png')

# ==============================================================================
# GRÁFICO 4: CAUSAS Y DURACIÓN DE COMBATE (Diapositiva 8)
# ==============================================================================
print("\nGenerando Gráfico 4: Causas y Duración de Combate (Panel Dual)...")
causas_principales = df_fires['Causa'].value_counts().head(6)
causas_pct = (causas_principales / len(df_fires)) * 100

df_dur = df_fires[(df_fires['Duracion_Horas'] > 0) & (df_fires['Duracion_Horas'] < 168) & (df_fires['Causa'].isin(causas_principales.index))]
dur_median = df_dur.groupby('Causa')['Duracion_Horas'].median().reindex(causas_principales.index)
dur_p90 = df_dur.groupby('Causa')['Duracion_Horas'].apply(lambda x: np.percentile(x, 90)).reindex(causas_principales.index)

fig, (ax_c, ax_d) = plt.subplots(1, 2, figsize=(13.5, 6.0), facecolor='#FFFFFF', gridspec_kw={'width_ratios': [1.2, 1]})

labels_clean = causas_principales.index.tolist()
causas_colors = [COLOR_PRIMARY if 'Intencionales' in c else ('#D97A6C' if 'Tránsito' in c else '#8FA3AD') for c in labels_clean]
bars_c = ax_c.barh(range(len(labels_clean)), causas_pct.values, color=causas_colors, height=0.62)
ax_c.set_yticks(range(len(labels_clean)))
ax_c.set_yticklabels(labels_clean, fontsize=10.5, color=COLOR_DARK_TEXT)
ax_c.invert_yaxis()
ax_c.set_xlabel('% del Total Nacional de Incendios', fontsize=11, fontweight='semibold', color=COLOR_DARK_TEXT)
ax_c.set_xlim(0, 42)
ax_c.set_title('A. Participación por Causa de Origen', fontsize=12, fontweight='bold', color=COLOR_DARK_TEXT, loc='left', pad=10)
ax_c.grid(axis='x', linestyle='--', alpha=0.35, color='#D0D7DE')
ax_c.spines['top'].set_visible(False)
ax_c.spines['right'].set_visible(False)

for bar, cnt in zip(bars_c, causas_principales.values):
    w = bar.get_width()
    ax_c.text(w + 0.8, bar.get_y() + bar.get_height()/2, f"{w:.1f}% ({int(cnt):,})", va='center', fontsize=9.5, fontweight='bold', color=COLOR_DARK_TEXT)

ax_c.text(0.96, 0.12, 'Origen Antrópico Directo:\nIntencional (32.9%) + Tránsito (29.9%)\n= 62.8% de todos los incendios',
          transform=ax_c.transAxes, fontsize=9.5, fontweight='bold', color=COLOR_PRIMARY,
          ha='right', va='bottom', bbox=dict(boxstyle='round,pad=0.6', facecolor='#FDF2F0', edgecolor='#EABDB4', alpha=0.95))

y_pos = np.arange(len(labels_clean))
bars_med = ax_d.barh(y_pos - 0.18, dur_median.values, height=0.34, color='#34495E', label='Mediana Típica')
bars_p90 = ax_d.barh(y_pos + 0.18, dur_p90.values, height=0.34, color='#E67E22', alpha=0.85, label='Casos Críticos (P90)')

ax_d.set_yticks(y_pos)
ax_d.set_yticklabels([])
ax_d.invert_yaxis()
ax_d.set_xlabel('Horas de Combate Activo', fontsize=11, fontweight='semibold', color=COLOR_DARK_TEXT)
ax_d.set_xlim(0, 24)
ax_d.set_title('B. Tiempo de Combate Activo (Horas)', fontsize=12, fontweight='bold', color=COLOR_DARK_TEXT, loc='left', pad=10)
ax_d.grid(axis='x', linestyle='--', alpha=0.35, color='#D0D7DE')
ax_d.spines['top'].set_visible(False)
ax_d.spines['right'].set_visible(False)
ax_d.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', edgecolor='#D0D7DE', fontsize=9.5)

for bar in bars_med:
    w = bar.get_width()
    ax_d.text(w + 0.3, bar.get_y() + bar.get_height()/2, f"{w:.1f}h", va='center', fontsize=8.5, fontweight='bold', color='#34495E')

for bar in bars_p90:
    w = bar.get_width()
    ax_d.text(w + 0.3, bar.get_y() + bar.get_height()/2, f"{w:.1f}h", va='center', fontsize=8.5, fontweight='bold', color='#D35400')

fig.suptitle('Causas de Ignición y Respuesta Operativa de Combate', fontsize=14, fontweight='bold', color=COLOR_DARK_TEXT, y=1.02)
plt.tight_layout()
save_plot(fig, 'grafico_4_causas_duracion.png')

# ==============================================================================
# GRÁFICO 5: INTERFAZ HUMANO-FORESTAL Y TOPOGRAFÍA (Diapositiva 9)
# ==============================================================================
print("\nGenerando Gráfico 5: Interfaz Humano-Forestal...")
geo_path = BASE_DIR / "data" / "processed" / "training_dataset_large_v3b.csv"
df_geo = pd.read_csv(geo_path)
fires = df_geo[df_geo['Fire_Probability'] == 1].copy()

fig, ax = plt.subplots(figsize=(10, 6.2), facecolor='#FFFFFF')
ax.set_facecolor('#FFFFFF')

ax.axvspan(0, 5, color='#FDF2F0', alpha=0.8, zorder=1)
ax.axvline(5, color=COLOR_PRIMARY, linestyle='--', lw=1.6, zorder=4, alpha=0.8)

sc = ax.scatter(
    fires['dist_nearest_town_km'],
    fires['slope_deg'],
    c=fires['temp_max_window'],
    cmap='YlOrRd',
    vmin=20,
    vmax=38,
    alpha=0.55,
    s=24,
    edgecolors='none',
    zorder=3
)

cbar = plt.colorbar(sc, ax=ax, pad=0.02)
cbar.set_label('Temperatura Máxima 7 días previos (°C)', fontweight='bold', color=COLOR_DARK_TEXT, fontsize=10)
cbar.ax.tick_params(labelsize=9)

ax.text(5.2, 32, '← Umbral Crítico: 5 km', fontsize=10.5, fontweight='bold', color=COLOR_PRIMARY, va='center')

info_box = (
    "Zona de Interfaz Urbano-Forestal:\n"
    "• 96.8% de igniciones a < 5 km\n"
    "• Distancia promedio: 2.1 km\n"
    "• Pendiente media: 9.1°\n"
    "Conclusión: No es un fenómeno remoto,\n"
    "sino de contacto directo con poblados."
)
ax.text(0.96, 0.72, info_box, transform=ax.transAxes, fontsize=10, fontweight='medium',
        color='#2C3E50', ha='right', va='center',
        bbox=dict(boxstyle='round,pad=0.7', facecolor='#FFFFFF', edgecolor=COLOR_PRIMARY, lw=1.2, alpha=0.96))

ax.set_title('Densidad de Ignición según Distancia a Centros Poblados y Pendiente', fontsize=13.5, fontweight='bold', pad=16, color=COLOR_DARK_TEXT, loc='left')
ax.set_xlabel('Distancia Geodésica al Centro Poblado más Cercano (km)', fontsize=11, fontweight='semibold', color=COLOR_DARK_TEXT, labelpad=8)
ax.set_ylabel('Pendiente del Terreno (Grados de Inclinación)', fontsize=11, fontweight='semibold', color=COLOR_DARK_TEXT, labelpad=8)
ax.set_xlim(0, 18)
ax.set_ylim(0, 36)
ax.grid(True, linestyle='--', alpha=0.3, color='#D0D7DE')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

save_plot(fig, 'grafico_5_antropico_topografia.png')

# ==============================================================================
# GRÁFICOS EXTRA
# ==============================================================================
print("\nGenerando Gráficos Extra...")

# Extra 1: Ciclo Horario Circadiano
df_fires['Hora'] = pd.to_datetime(df_fires['Hora inicio'], format='%H:%M', errors='coerce').dt.hour
hora_counts = df_fires['Hora'].value_counts().sort_index()

fig, ax = plt.subplots(figsize=(10, 5), facecolor='#FFFFFF')
bar_c = [COLOR_PRIMARY if (13 <= h <= 18) else '#4A6572' for h in hora_counts.index]
ax.bar(hora_counts.index, hora_counts.values, color=bar_c, width=0.7, edgecolor='none')
ax.axvspan(12.5, 18.5, color='#FDF2F0', alpha=0.6, zorder=0)

ax.set_title('Distribución Horaria de Inicio de Incendios: La Ventana Crítica (13:00–18:00)', fontsize=13, fontweight='bold', color=COLOR_DARK_TEXT, pad=14, loc='left')
ax.set_xlabel('Hora del Día (00:00 a 23:00 hrs)', fontsize=11, fontweight='semibold')
ax.set_ylabel('Total de Incendios Iniciados', fontsize=11, fontweight='semibold')
ax.set_xticks(range(0, 24))
ax.grid(axis='y', linestyle='--', alpha=0.35)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax.text(0.96, 0.78, 'Ventana 13:00 – 18:00 hrs:\nConcentra el 71.4% de los inicios\n(Coincide con Regla 30-30-30:\n>30°C, <30% HR, viento vespertino)',
        transform=ax.transAxes, fontsize=9.5, fontweight='medium', color=COLOR_PRIMARY, ha='right',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFFFFF', edgecolor=COLOR_PRIMARY, alpha=0.95))

save_plot(fig, 'grafico_extra_ciclo_horario.png')

# Extra 2: Matriz de Correlación
num_cols = ['temp_max_window', 'humidity_min_window', 'wind_speed_max_window', 'dist_nearest_town_km', 'slope_deg', 'soil_moisture_mean', 'Fire_Probability']
col_names = ['Temp Máx', 'Humedad Mín', 'Viento Máx', 'Dist Poblado', 'Pendiente', 'Humedad Suelo', 'Incendio (0/1)']
corr = df_geo[num_cols].corr()

fig, ax = plt.subplots(figsize=(8, 6.5), facecolor='#FFFFFF')
im = ax.imshow(corr, cmap='coolwarm', vmin=-0.8, vmax=0.8)
cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label('Coeficiente de Pearson (r)', fontweight='bold')

ax.set_xticks(range(len(num_cols)))
ax.set_yticks(range(len(num_cols)))
ax.set_xticklabels(col_names, rotation=35, ha='right', fontsize=9.5, fontweight='semibold')
ax.set_yticklabels(col_names, fontsize=9.5, fontweight='semibold')

for i in range(len(num_cols)):
    for j in range(len(num_cols)):
        val = corr.iloc[i, j]
        ax.text(j, i, f"{val:.2f}", ha='center', va='center',
                color='white' if abs(val) > 0.4 else 'black', fontweight='bold', fontsize=9)

ax.set_title('Matriz de Correlación de Variables Físico-Climáticas', fontsize=13, fontweight='bold', pad=14, color=COLOR_DARK_TEXT)
save_plot(fig, 'grafico_extra_correlacion.png')

# Extra 3: Cartografía Geoespacial y Epicentros
print("Generando Gráfico Extra: Mapa Geoespacial de Focos...")
df_map = df_fires.dropna(subset=['Latitud', 'Longitud']).copy()
df_map['Latitud'] = pd.to_numeric(df_map['Latitud'], errors='coerce')
df_map['Longitud'] = pd.to_numeric(df_map['Longitud'], errors='coerce')
df_map = df_map[(df_map['Latitud'] >= -56) & (df_map['Latitud'] <= -18) & (df_map['Longitud'] >= -76) & (df_map['Longitud'] <= -66)]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 8), gridspec_kw={'width_ratios': [1, 1.4]}, facecolor='#FFFFFF')
ax1.set_facecolor('#FFFFFF')
ax2.set_facecolor('#FFFFFF')

# 1. Mapa Nacional
sc1 = ax1.scatter(df_map['Longitud'], df_map['Latitud'], c=np.log1p(df_map['Superficie quemada total [ha]']), cmap='hot_r', alpha=0.35, s=4)
ax1.set_title('Densidad Nacional de Incendios en Chile\n(109.985 Focos Históricos)', fontweight='bold', fontsize=11, color=COLOR_DARK_TEXT)
ax1.set_xlabel('Longitud (°O)', fontweight='semibold')
ax1.set_ylabel('Latitud (°S)', fontweight='semibold')
ax1.set_xlim(-76, -66)
ax1.set_ylim(-56, -18)
ax1.grid(True, linestyle='--', alpha=0.3)

# 2. Zona Centro-Sur
zona_critica = df_map[(df_map['Latitud'] >= -40) & (df_map['Latitud'] <= -32)]
sc2 = ax2.scatter(
    zona_critica['Longitud'],
    zona_critica['Latitud'],
    c=zona_critica['Superficie quemada total [ha]'],
    cmap='YlOrRd',
    vmin=0,
    vmax=500,
    alpha=0.55,
    s=zona_critica['Superficie quemada total [ha]'].clip(8, 120)
)
cbar = plt.colorbar(sc2, ax=ax2, pad=0.02)
cbar.set_label('Superficie Quemada (ha)', fontweight='bold', color=COLOR_DARK_TEXT)
ax2.set_title('Zona Crítica Centro-Sur (Valparaíso a La Araucanía)\nConcentra el 89.7% del Daño Nacional', fontweight='bold', fontsize=11, color=COLOR_DARK_TEXT)
ax2.set_xlabel('Longitud (°O)', fontweight='semibold')
ax2.set_ylabel('Latitud (°S)', fontweight='semibold')
ax2.set_xlim(-74, -70)
ax2.set_ylim(-40, -32)
ax2.grid(True, linestyle='--', alpha=0.3)

reg_coords = {
    'Valparaíso': (-71.6, -33.0),
    'Metropolitana': (-70.6, -33.5),
    'Maule': (-71.6, -35.4),
    'Biobío': (-72.5, -36.8),
    'Araucanía': (-72.6, -38.7)
}
for r_name, (lon, lat) in reg_coords.items():
    ax2.plot(lon, lat, 'ko', markersize=4)
    ax2.text(lon + 0.15, lat, r_name, fontsize=9.5, fontweight='bold', color='#1A202C')

plt.tight_layout()
save_plot(fig, 'grafico_extra_mapa_geoespacial.png')

print("\n¡Todos los 8 gráficos fueron generados y guardados con éxito total!")
