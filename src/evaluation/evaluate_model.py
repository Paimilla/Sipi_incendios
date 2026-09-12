"""
Evaluación Avanzada del Modelo XGBoost — SIpi Incendios
========================================================
Genera métricas avanzadas, gráficos de diagnóstico y un reporte JSON
consolidado para consumo del dashboard.

Evaluaciones:
  1. Curva Precision-Recall
  2. Calibración del modelo
  3. Distribución de probabilidades por clase
  4. Rendimiento por estación del año
  5. Rendimiento por región latitudinal
  6. Análisis de errores (scatter geográfico)
  7. SHAP summary (opcional)
  8. Reporte JSON consolidado
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sklearn.metrics import (
    precision_recall_curve, average_precision_score,
    roc_auc_score, f1_score, accuracy_score,
    classification_report, confusion_matrix,
    brier_score_loss
)
from sklearn.calibration import calibration_curve
import joblib
import warnings
warnings.filterwarnings('ignore')

from config import DATASET_V3B, MODELS_DIR, BURNABLE_CLASSES

# ── Configuración ──────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent
TEMPORAL_SPLIT_YEAR = 2019
TEST_MAX_YEAR = 2020

# Paleta de colores consistente
COLORS = {
    'primary': '#E65100',
    'secondary': '#FF8F00',
    'accent': '#FFD54F',
    'dark': '#1A1A2E',
    'fire': '#D84315',
    'safe': '#2E7D32',
    'neutral': '#78909C',
    'bg': '#0F0F1A',
    'grid': '#333355',
}

SEASON_NAMES = {1: 'Verano', 2: 'Otoño', 3: 'Invierno', 4: 'Primavera'}
REGION_BINS = [
    (-56.0, -43.0, 'Austral'),
    (-43.0, -35.0, 'Sur'),
    (-35.0, -30.0, 'Centro'),
    (-30.0, -17.0, 'Norte'),
]


def styled_figure(figsize=(10, 7)):
    """Crea una figura con estilo oscuro premium."""
    fig, ax = plt.subplots(figsize=figsize, facecolor=COLORS['bg'])
    ax.set_facecolor(COLORS['bg'])
    ax.tick_params(colors='#CCCCCC', which='both')
    ax.xaxis.label.set_color('#CCCCCC')
    ax.yaxis.label.set_color('#CCCCCC')
    ax.title.set_color('#EEEEEE')
    for spine in ax.spines.values():
        spine.set_color(COLORS['grid'])
    ax.grid(True, alpha=0.2, color=COLORS['grid'])
    return fig, ax


def add_temporal_features(df):
    """Replica exactamente las features del entrenamiento."""
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['year'] = df['Fecha'].dt.year
    df['month'] = df['Fecha'].dt.month
    df['day_of_year'] = df['Fecha'].dt.dayofyear

    def get_season(month):
        if month in [12, 1, 2, 3]:
            return 1
        elif month in [4, 5]:
            return 2
        elif month in [6, 7, 8]:
            return 3
        else:
            return 4

    df['season'] = df['month'].apply(get_season)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    return df


def add_climate_interaction_features(df):
    """Replica las features derivadas del entrenamiento."""
    df['dryness_index'] = df['temp_max_window'] * (100 - df['humidity_mean_window']) / 100
    df['precip_drought'] = (df['precip_acc_window'] < 1.0).astype(int)
    df['temp_humidity_ratio'] = df['temp_max_window'] / (df['humidity_min_window'] + 1)
    df['fire_weather_index'] = (
        df['temp_max_window'] * df['wind_speed_max_window']
        / (df['humidity_min_window'] + 1)
    )
    return df


def assign_region(lat):
    """Asigna región latitudinal."""
    for lat_min, lat_max, name in REGION_BINS:
        if lat_min <= lat < lat_max:
            return name
    return 'Otro'


def load_and_prepare():
    """Carga modelo y datos, reproduce el split temporal."""
    print("Cargando modelo y datos...")
    model = joblib.load(MODELS_DIR / 'xgboost_fire_model_final.pkl')
    metadata = joblib.load(MODELS_DIR / 'model_metadata_final.pkl')

    df = pd.read_csv(DATASET_V3B)
    df = df.dropna(subset=['elevation'])
    df = df[
        (df['Fire_Probability'] == 1)
        | ((df['Fire_Probability'] == 0) & (df['land_cover_class'].isin(BURNABLE_CLASSES)))
    ]

    df = add_temporal_features(df)
    df = add_climate_interaction_features(df)
    df = df.reset_index(drop=True)

    features = metadata['features']

    test_mask = (df['year'] >= TEMPORAL_SPLIT_YEAR) & (df['year'] <= TEST_MAX_YEAR)
    test_df = df[test_mask].copy()

    X_test = test_df[features].copy()
    X_test['land_cover_class'] = X_test['land_cover_class'].astype('category')
    y_test = test_df['Fire_Probability'].values

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)

    print(f"  Test set: {len(test_df)} muestras ({test_df['year'].min()}-{test_df['year'].max()})")
    return model, metadata, test_df, X_test, y_test, y_prob, y_pred, features


# ── 1. Precision-Recall Curve ──────────────────────────────────────────
def plot_precision_recall(y_test, y_prob):
    precision, recall, thresholds = precision_recall_curve(y_test, y_prob)
    ap = average_precision_score(y_test, y_prob)

    fig, ax = styled_figure()
    ax.plot(recall, precision, color=COLORS['primary'], lw=2.5,
            label=f'PR Curve (AP = {ap:.4f})')
    ax.axhline(y=y_test.mean(), color=COLORS['neutral'], ls='--', lw=1,
               label=f'Baseline (prevalencia = {y_test.mean():.2f})')
    ax.set_xlabel('Recall', fontsize=13)
    ax.set_ylabel('Precision', fontsize=13)
    ax.set_title('Curva Precision-Recall — Validación Temporal', fontsize=15, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11, facecolor=COLORS['dark'], edgecolor=COLORS['grid'])
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.05])
    fig.tight_layout()
    path = OUTPUT_DIR / 'precision_recall_curve.png'
    fig.savefig(path, dpi=150, facecolor=COLORS['bg'])
    plt.close(fig)
    print(f"  ✓ Precision-Recall → {path.name} (AP={ap:.4f})")
    return ap


# ── 2. Calibración ────────────────────────────────────────────────────
def plot_calibration(y_test, y_prob):
    fraction_positive, mean_predicted = calibration_curve(y_test, y_prob, n_bins=10)
    brier = brier_score_loss(y_test, y_prob)

    fig, ax = styled_figure()
    ax.plot(mean_predicted, fraction_positive, 's-', color=COLORS['secondary'],
            lw=2, markersize=8, label=f'Modelo (Brier={brier:.4f})')
    ax.plot([0, 1], [0, 1], 'k--', lw=1, color=COLORS['neutral'],
            label='Calibración perfecta')
    ax.set_xlabel('Probabilidad Predicha (media del bin)', fontsize=13)
    ax.set_ylabel('Fracción de Positivos Reales', fontsize=13)
    ax.set_title('Curva de Calibración del Modelo', fontsize=15, fontweight='bold')
    ax.legend(loc='lower right', fontsize=11, facecolor=COLORS['dark'], edgecolor=COLORS['grid'])
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.05])
    fig.tight_layout()
    path = OUTPUT_DIR / 'calibration_curve.png'
    fig.savefig(path, dpi=150, facecolor=COLORS['bg'])
    plt.close(fig)
    print(f"  ✓ Calibración → {path.name} (Brier={brier:.4f})")
    return brier


# ── 3. Distribución de probabilidades ─────────────────────────────────
def plot_probability_distribution(y_test, y_prob):
    fig, ax = styled_figure()
    ax.hist(y_prob[y_test == 0], bins=40, alpha=0.7, color=COLORS['safe'],
            label='No Incendio (real)', density=True, edgecolor='none')
    ax.hist(y_prob[y_test == 1], bins=40, alpha=0.7, color=COLORS['fire'],
            label='Incendio (real)', density=True, edgecolor='none')
    ax.axvline(x=0.5, color=COLORS['accent'], ls='--', lw=1.5, label='Umbral 0.5')
    ax.set_xlabel('Probabilidad Predicha', fontsize=13)
    ax.set_ylabel('Densidad', fontsize=13)
    ax.set_title('Distribución de Probabilidades por Clase Real', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, facecolor=COLORS['dark'], edgecolor=COLORS['grid'])
    fig.tight_layout()
    path = OUTPUT_DIR / 'probability_distribution.png'
    fig.savefig(path, dpi=150, facecolor=COLORS['bg'])
    plt.close(fig)
    print(f"  ✓ Distribución probabilidades → {path.name}")


# ── 4. Rendimiento por estación ───────────────────────────────────────
def plot_performance_by_season(test_df, y_test, y_prob, y_pred):
    seasons = []
    f1s = []
    aucs = []
    counts = []

    for s_code, s_name in SEASON_NAMES.items():
        mask = test_df['season'].values == s_code
        if mask.sum() < 5:
            continue
        y_t = y_test[mask]
        y_p = y_pred[mask]
        y_pr = y_prob[mask]
        if len(np.unique(y_t)) < 2:
            continue
        seasons.append(s_name)
        f1s.append(f1_score(y_t, y_p))
        aucs.append(roc_auc_score(y_t, y_pr))
        counts.append(int(mask.sum()))

    if not seasons:
        print("  ⚠ No hay suficientes datos por estación para graficar")
        return {}

    fig, ax = styled_figure((10, 6))
    x = np.arange(len(seasons))
    w = 0.35
    bars1 = ax.bar(x - w / 2, f1s, w, color=COLORS['primary'], label='F1 Score', alpha=0.9)
    bars2 = ax.bar(x + w / 2, aucs, w, color=COLORS['secondary'], label='ROC-AUC', alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels([f'{s}\n(n={c})' for s, c in zip(seasons, counts)], fontsize=12)
    ax.set_ylabel('Métrica', fontsize=13)
    ax.set_title('Rendimiento del Modelo por Estación', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, facecolor=COLORS['dark'], edgecolor=COLORS['grid'])
    ax.set_ylim([0, 1.1])

    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., h + 0.02,
                    f'{h:.2f}', ha='center', va='bottom', fontsize=10, color='#CCCCCC')

    fig.tight_layout()
    path = OUTPUT_DIR / 'performance_by_season.png'
    fig.savefig(path, dpi=150, facecolor=COLORS['bg'])
    plt.close(fig)
    print(f"  ✓ Rendimiento por estación → {path.name}")
    return dict(zip(seasons, [{'f1': f, 'auc': a, 'n': c} for f, a, c in zip(f1s, aucs, counts)]))


# ── 5. Rendimiento por región ─────────────────────────────────────────
def plot_performance_by_region(test_df, y_test, y_prob, y_pred):
    regions = []
    f1s = []
    aucs = []
    counts = []

    test_regions = test_df['Latitud'].apply(assign_region).values

    for _, _, r_name in REGION_BINS:
        mask = test_regions == r_name
        if mask.sum() < 5:
            continue
        y_t = y_test[mask]
        y_p = y_pred[mask]
        y_pr = y_prob[mask]
        if len(np.unique(y_t)) < 2:
            continue
        regions.append(r_name)
        f1s.append(f1_score(y_t, y_p))
        aucs.append(roc_auc_score(y_t, y_pr))
        counts.append(int(mask.sum()))

    if not regions:
        print("  ⚠ No hay suficientes datos por región para graficar")
        return {}

    fig, ax = styled_figure((10, 6))
    x = np.arange(len(regions))
    w = 0.35
    bars1 = ax.bar(x - w / 2, f1s, w, color=COLORS['primary'], label='F1 Score', alpha=0.9)
    bars2 = ax.bar(x + w / 2, aucs, w, color=COLORS['secondary'], label='ROC-AUC', alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels([f'{r}\n(n={c})' for r, c in zip(regions, counts)], fontsize=12)
    ax.set_ylabel('Métrica', fontsize=13)
    ax.set_title('Rendimiento del Modelo por Región Latitudinal', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, facecolor=COLORS['dark'], edgecolor=COLORS['grid'])
    ax.set_ylim([0, 1.1])

    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., h + 0.02,
                    f'{h:.2f}', ha='center', va='bottom', fontsize=10, color='#CCCCCC')

    fig.tight_layout()
    path = OUTPUT_DIR / 'performance_by_region.png'
    fig.savefig(path, dpi=150, facecolor=COLORS['bg'])
    plt.close(fig)
    print(f"  ✓ Rendimiento por región → {path.name}")
    return dict(zip(regions, [{'f1': f, 'auc': a, 'n': c} for f, a, c in zip(f1s, aucs, counts)]))


# ── 6. Análisis de errores (scatter geográfico) ───────────────────────
def plot_error_analysis(test_df, y_test, y_pred):
    tp_mask = (y_test == 1) & (y_pred == 1)
    tn_mask = (y_test == 0) & (y_pred == 0)
    fp_mask = (y_test == 0) & (y_pred == 1)
    fn_mask = (y_test == 1) & (y_pred == 0)

    fig, ax = styled_figure((10, 12))

    ax.scatter(test_df.loc[test_df.index[tn_mask], 'Longitud'],
               test_df.loc[test_df.index[tn_mask], 'Latitud'],
               c=COLORS['safe'], alpha=0.3, s=15, label=f'TN ({tn_mask.sum()})', zorder=1)
    ax.scatter(test_df.loc[test_df.index[tp_mask], 'Longitud'],
               test_df.loc[test_df.index[tp_mask], 'Latitud'],
               c=COLORS['accent'], alpha=0.5, s=20, label=f'TP ({tp_mask.sum()})', zorder=2)
    ax.scatter(test_df.loc[test_df.index[fp_mask], 'Longitud'],
               test_df.loc[test_df.index[fp_mask], 'Latitud'],
               c=COLORS['secondary'], alpha=0.8, s=30, marker='x',
               label=f'FP ({fp_mask.sum()})', zorder=3)
    ax.scatter(test_df.loc[test_df.index[fn_mask], 'Longitud'],
               test_df.loc[test_df.index[fn_mask], 'Latitud'],
               c=COLORS['fire'], alpha=0.9, s=40, marker='^',
               label=f'FN ({fn_mask.sum()})', zorder=4)

    ax.set_xlabel('Longitud', fontsize=13)
    ax.set_ylabel('Latitud', fontsize=13)
    ax.set_title('Análisis Geográfico de Errores del Modelo', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, loc='lower left', facecolor=COLORS['dark'], edgecolor=COLORS['grid'])
    ax.set_aspect('equal')
    fig.tight_layout()
    path = OUTPUT_DIR / 'error_analysis.png'
    fig.savefig(path, dpi=150, facecolor=COLORS['bg'])
    plt.close(fig)

    error_stats = {
        'true_positives': int(tp_mask.sum()),
        'true_negatives': int(tn_mask.sum()),
        'false_positives': int(fp_mask.sum()),
        'false_negatives': int(fn_mask.sum()),
    }
    print(f"  ✓ Análisis de errores → {path.name}")
    return error_stats


# ── 7. SHAP (opcional) ────────────────────────────────────────────────
def plot_shap_summary(model, X_test, features):
    try:
        import shap
    except ImportError:
        print("  ⚠ shap no instalado — omitiendo SHAP analysis")
        return False

    print("  Calculando SHAP values (puede tomar unos minutos)...")
    try:
        # Usar TreeExplainer para XGBoost (rápido)
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)

        fig = plt.figure(figsize=(12, 8), facecolor=COLORS['bg'])
        shap.summary_plot(shap_values, X_test, feature_names=features,
                          show=False, plot_size=None)
        ax = plt.gca()
        ax.set_facecolor(COLORS['bg'])
        ax.tick_params(colors='#CCCCCC')
        ax.set_title('SHAP Feature Importance', fontsize=15, fontweight='bold', color='#EEEEEE')
        fig.tight_layout()
        path = OUTPUT_DIR / 'shap_summary.png'
        fig.savefig(path, dpi=150, facecolor=COLORS['bg'], bbox_inches='tight')
        plt.close(fig)
        print(f"  ✓ SHAP summary → {path.name}")
        return True
    except Exception as e:
        print(f"  ⚠ Error generando SHAP: {e}")
        return False


# ── 8. Reporte JSON ───────────────────────────────────────────────────
def generate_report(metadata, y_test, y_prob, y_pred, ap, brier,
                    season_perf, region_perf, error_stats, shap_available):
    """Genera reporte consolidado JSON."""
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred,
                                   target_names=['No Incendio', 'Incendio'],
                                   output_dict=True)

    evaluation = {
        'model_version': metadata.get('version', 'V2'),
        'train_years': metadata.get('train_years', ''),
        'test_years': metadata.get('test_years', ''),
        'train_samples': metadata.get('train_samples', 0),
        'test_samples': metadata.get('test_samples', 0),
        'features': metadata.get('features', []),
        'metrics': {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'f1_score': float(f1_score(y_test, y_pred)),
            'roc_auc': float(roc_auc_score(y_test, y_prob)),
            'average_precision': float(ap),
            'brier_score': float(brier),
        },
        'confusion_matrix': {
            'true_negatives': int(cm[0, 0]),
            'false_positives': int(cm[0, 1]),
            'false_negatives': int(cm[1, 0]),
            'true_positives': int(cm[1, 1]),
        },
        'classification_report': {
            k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                 for kk, vv in v.items()} if isinstance(v, dict) else round(v, 4)
            for k, v in report.items()
        },
        'performance_by_season': season_perf,
        'performance_by_region': region_perf,
        'error_analysis': error_stats,
        'shap_available': shap_available,
        'plots': [
            'precision_recall_curve.png',
            'calibration_curve.png',
            'probability_distribution.png',
            'performance_by_season.png',
            'performance_by_region.png',
            'error_analysis.png',
        ] + (['shap_summary.png'] if shap_available else []),
    }

    path = OUTPUT_DIR / 'evaluation_report.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Reporte JSON → {path.name}")
    return evaluation


# ── Main ──────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("   EVALUACIÓN AVANZADA — SIpi Incendios")
    print("=" * 60)

    model, metadata, test_df, X_test, y_test, y_prob, y_pred, features = load_and_prepare()

    print(f"\nGenerando evaluaciones en {OUTPUT_DIR}/\n")

    ap = plot_precision_recall(y_test, y_prob)
    brier = plot_calibration(y_test, y_prob)
    plot_probability_distribution(y_test, y_prob)
    season_perf = plot_performance_by_season(test_df, y_test, y_prob, y_pred)
    region_perf = plot_performance_by_region(test_df, y_test, y_prob, y_pred)
    error_stats = plot_error_analysis(test_df, y_test, y_pred)
    shap_ok = plot_shap_summary(model, X_test, features)

    report = generate_report(metadata, y_test, y_prob, y_pred,
                             ap, brier, season_perf, region_perf,
                             error_stats, shap_ok)

    print("\n" + "=" * 60)
    print("  RESUMEN DE MÉTRICAS")
    print("=" * 60)
    for k, v in report['metrics'].items():
        print(f"  {k:25s}: {v:.4f}")
    print("=" * 60)
    print("  Evaluación completada exitosamente ✓")


if __name__ == '__main__':
    main()
