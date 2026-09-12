"""
1. TEMPORAL SPLIT LIMPIO: Test solo incluye años con datos de ambas clases (2019-2020)
2. SAMPLE WEIGHTS: Negativos de invierno reciben peso menor (sin perder datos)
3. SMART NEGATIVE SAMPLING: Solo negativos en zonas quemables
4. OPTUNA TUNING: 80 trials con sample_weight integrado en CV + reg_alpha/reg_lambda
5. METRICAS COMPLETAS: Reporta metricas por clase, curva ROC, y matriz de confusion
6. FEATURE ENGINEERING: Indices de interaccion climatica (dryness, drought, fire weather)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import optuna
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, 
                             classification_report, confusion_matrix, roc_curve)
import joblib
import warnings
warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

from config import DATASET_V3B, MODELS_DIR, BURNABLE_CLASSES

TEMPORAL_SPLIT_YEAR = 2019
# Solo evaluar en años donde existen datos reales de ambas clases
TEST_MAX_YEAR = 2020
OPTUNA_TRIALS = 80


def add_temporal_features(df):
    """Features temporales con encoding ciclico."""
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['year'] = df['Fecha'].dt.year
    df['month'] = df['Fecha'].dt.month
    df['day_of_year'] = df['Fecha'].dt.dayofyear
    
    def get_season(month):
        if month in [12, 1, 2, 3]: return 1
        elif month in [4, 5]: return 2
        elif month in [6, 7, 8]: return 3
        else: return 4
    
    df['season'] = df['month'].apply(get_season)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    return df


def add_climate_interaction_features(df):
    """
    Features de interaccion climatica derivadas.
    Capturan combinaciones no lineales que los arboles tardan mas en descubrir.
    Validado empiricamente: Cohen's d entre 0.48 y 0.87.
    """
    # Indice de sequedad: temp alta + baja humedad = alto riesgo
    df['dryness_index'] = df['temp_max_window'] * (100 - df['humidity_mean_window']) / 100
    
    # Indicador binario de sequia: <1mm en 7 dias
    df['precip_drought'] = (df['precip_acc_window'] < 1.0).astype(int)
    
    # Ratio temperatura/humedad: condiciones de evaporacion extrema
    df['temp_humidity_ratio'] = df['temp_max_window'] / (df['humidity_min_window'] + 1)
    
    # Indice compuesto de clima de incendio: calor + viento + sequedad
    df['fire_weather_index'] = (df['temp_max_window'] * df['wind_speed_max_window'] 
                                / (df['humidity_min_window'] + 1))
    
    return df


def compute_sample_weights(df):
    """
    Asigna pesos a cada muestra para corregir el sesgo temporal
    sin eliminar datos. Los negativos de meses con pocos positivos
    reciben peso menor.
    
    Version vectorizada (reemplaza iterrows lento).
    """
    positives = df[df['Fire_Probability'] == 1]
    negatives = df[df['Fire_Probability'] == 0]
    
    pos_month_dist = positives['month'].value_counts(normalize=True)
    neg_month_dist = negatives['month'].value_counts(normalize=True)
    
    # Calcular ratio de peso por mes
    weight_by_month = {}
    for month in range(1, 13):
        pos_prop = pos_month_dist.get(month, 0.01)
        neg_prop = neg_month_dist.get(month, 0.01)
        weight_by_month[month] = max(0.1, pos_prop / neg_prop)
    
    # Vectorizado: positivos reciben peso 1.0, negativos reciben peso segun mes
    weights = np.ones(len(df))
    neg_mask = df['Fire_Probability'] == 0
    weights[neg_mask.values] = df.loc[neg_mask, 'month'].map(weight_by_month).values
    
    return weights


def objective(trial, X_train, y_train, w_train):
    """
    Optuna objective con validacion interna (solo sobre datos de entrenamiento).
    Ahora pasa sample_weight a cada fold para que los hiperparametros
    se optimicen bajo el mismo regimen de pesos del entrenamiento final.
    """
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 800),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'gamma': trial.suggest_float('gamma', 0.0, 5.0),
        'scale_pos_weight': trial.suggest_float('scale_pos_weight', 0.5, 2.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'random_state': 42,
        'eval_metric': 'logloss',
        'enable_categorical': True,
        'tree_method': 'hist',
    }
    
    # CV manual para poder pasar sample_weight a fit()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = []
    
    for train_idx, val_idx in cv.split(X_train, y_train):
        X_fold_train = X_train.iloc[train_idx]
        y_fold_train = y_train.iloc[train_idx]
        w_fold_train = w_train[train_idx]
        X_fold_val = X_train.iloc[val_idx]
        y_fold_val = y_train.iloc[val_idx]
        
        model = XGBClassifier(**params)
        model.fit(X_fold_train, y_fold_train, sample_weight=w_fold_train)
        
        y_prob = model.predict_proba(X_fold_val)[:, 1]
        auc_scores.append(roc_auc_score(y_fold_val, y_prob))
    
    return np.mean(auc_scores)


def plot_roc_curve(y_test, y_prob, save_path):
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    auc_val = roc_auc_score(y_test, y_prob)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='#8e44ad', lw=2, label=f'ROC Curve (AUC = {auc_val:.4f})')
    plt.plot([0, 1], [0, 1], 'k--', lw=1, label='Random (AUC = 0.5)')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate', fontsize=12)
    plt.ylabel('True Positive Rate', fontsize=12)
    plt.title('Curva ROC - Modelo Final V2 (Validacion Temporal)', fontsize=14)
    plt.legend(loc='lower right', fontsize=11)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_confusion_matrix(y_test, y_pred, save_path):
    cm = confusion_matrix(y_test, y_pred)
    
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation='nearest', cmap='Purples')
    plt.title('Matriz de Confusion - Modelo Final V2', fontsize=14)
    plt.colorbar()
    classes = ['No Incendio', 'Incendio']
    tick_marks = [0, 1]
    plt.xticks(tick_marks, classes, fontsize=11)
    plt.yticks(tick_marks, classes, fontsize=11)
    
    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(cm[i, j]), ha='center', va='center', 
                     fontsize=16, fontweight='bold',
                     color='white' if cm[i, j] > cm.max()/2 else 'black')
    
    plt.ylabel('Real', fontsize=12)
    plt.xlabel('Prediccion', fontsize=12)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def train_final():
    print("=" * 60)
    print("   MODELO FINAL V2 -- AUDITADO, CORREGIDO Y MEJORADO")
    print("=" * 60)
    
    print(f"\nCargando dataset desde {DATASET_V3B}...")
    df = pd.read_csv(DATASET_V3B)
    df = df.dropna(subset=['elevation'])
    initial_len = len(df)
    
    # --- SMART NEGATIVE SAMPLING ---
    df = df[(df['Fire_Probability'] == 1) | 
            ((df['Fire_Probability'] == 0) & (df['land_cover_class'].isin(BURNABLE_CLASSES)))]
    print(f"Smart Sampling: {initial_len} -> {len(df)} registros (removidos negativos no quemables)")
    
    # --- TEMPORAL FEATURES ---
    df = add_temporal_features(df)
    
    # --- CLIMATE INTERACTION FEATURES (Mejora 2) ---
    df = add_climate_interaction_features(df)
    df = df.reset_index(drop=True)
    
    print(f"Positivos: {len(df[df['Fire_Probability']==1])}")
    print(f"Negativos: {len(df[df['Fire_Probability']==0])}")
    
    # --- SAMPLE WEIGHTS (corrige sesgo temporal sin eliminar datos) ---
    sample_weights = compute_sample_weights(df)
    print(f"Sample weights calculados (min={sample_weights.min():.2f}, max={sample_weights.max():.2f})")
    
    # --- TEMPORAL SPLIT (sin data leakage) ---
    # Mejora 1: Test solo incluye años con datos de ambas clases
    train_mask = df['year'] < TEMPORAL_SPLIT_YEAR
    test_mask = (df['year'] >= TEMPORAL_SPLIT_YEAR) & (df['year'] <= TEST_MAX_YEAR)
    
    train_df = df[train_mask]
    test_df = df[test_mask]
    
    # Verificar que el test set tiene ambas clases
    test_pos = int(test_df['Fire_Probability'].sum())
    test_neg = int((test_df['Fire_Probability'] == 0).sum())
    if test_pos == 0 or test_neg == 0:
        print("ADVERTENCIA: El test set no tiene ambas clases. Revise TEST_MAX_YEAR.")
    
    print(f"\n--- TEMPORAL SPLIT (Corte: {TEMPORAL_SPLIT_YEAR}, Test hasta: {TEST_MAX_YEAR}) ---")
    print(f"  Train: {len(train_df)} registros ({train_df['year'].min()}-{train_df['year'].max()})")
    print(f"  Test:  {len(test_df)} registros ({test_df['year'].min()}-{test_df['year'].max()})")
    print(f"  Train -> pos: {int(train_df['Fire_Probability'].sum())}, neg: {int((train_df['Fire_Probability']==0).sum())}")
    print(f"  Test  -> pos: {test_pos}, neg: {test_neg}")
    
    # Datos excluidos del test por no tener positivos
    excluded = df[(df['year'] > TEST_MAX_YEAR)]
    if len(excluded) > 0:
        print(f"  Excluidos del test (sin positivos): {len(excluded)} registros ({excluded['year'].min()}-{excluded['year'].max()})")
    
    features = [
        'temp_max_window', 'temp_mean_window', 'humidity_min_window', 'humidity_mean_window',
        'precip_acc_window', 'wind_speed_max_window', 'wind_speed_mean_window', 
        'soil_temp_mean', 'soil_moisture_mean',
        'land_cover_class', 'dist_nearest_town_km', 'elevation', 'slope_deg', 'aspect_deg',
        'month_sin', 'month_cos', 'day_of_year', 'season',
        # Nuevas features de interaccion climatica (Mejora 2)
        'dryness_index', 'precip_drought', 'temp_humidity_ratio', 'fire_weather_index'
    ]
    
    X_train = train_df[features].copy()
    y_train = train_df['Fire_Probability'].reset_index(drop=True)
    w_train = sample_weights[train_mask.values]
    X_test = test_df[features].copy()
    y_test = test_df['Fire_Probability']
    
    X_train['land_cover_class'] = X_train['land_cover_class'].astype('category')
    X_test['land_cover_class'] = X_test['land_cover_class'].astype('category')
    X_train = X_train.reset_index(drop=True)
    
    # --- OPTUNA (solo sobre datos de entrenamiento, con sample_weight) ---
    print("\n" + "=" * 60)
    print(f"Optimizacion de Hiperparametros (Optuna, {OPTUNA_TRIALS} trials)")
    print("Solo sobre datos PRE-2019 (sin tocar test set)")
    print("Sample weights integrados en cada fold de CV")
    print("=" * 60)
    
    study = optuna.create_study(direction='maximize')
    study.optimize(
        lambda trial: objective(trial, X_train, y_train, w_train), 
        n_trials=OPTUNA_TRIALS
    )
    
    print(f"\nMejor ROC-AUC interno (CV sobre train): {study.best_value:.4f}")
    
    best_params = study.best_params
    best_params['random_state'] = 42
    best_params['eval_metric'] = 'logloss'
    best_params['enable_categorical'] = True
    best_params['tree_method'] = 'hist'
    
    print(f"Mejores hiperparametros:")
    for k, v in best_params.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.6f}")
        else:
            print(f"  {k}: {v}")
    
    # --- ENTRENAMIENTO Y EVALUACION FINAL ---
    print("\n" + "=" * 60)
    print(f"Evaluacion Final sobre datos FUTUROS ({TEMPORAL_SPLIT_YEAR}-{TEST_MAX_YEAR})")
    print("=" * 60)
    
    best_model = XGBClassifier(**best_params)
    best_model.fit(X_train, y_train, sample_weight=w_train)
    
    y_pred = best_model.predict(X_test)
    y_prob = best_model.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    
    print(f"\n{'='*40}")
    print(f"  RESULTADOS SOBRE DATOS FUTUROS")
    print(f"  (El modelo NUNCA vio estos datos)")
    print(f"{'='*40}")
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  ROC-AUC:   {auc:.4f}")
    print(f"{'='*40}")
    
    print("\nReporte de Clasificacion Detallado:")
    print(classification_report(y_test, y_pred, target_names=['No Incendio', 'Incendio']))
    
    # --- GRAFICOS ---
    plt.figure(figsize=(12, 8))
    feat_importances = pd.Series(best_model.feature_importances_, index=features)
    feat_importances.nlargest(22).plot(kind='barh', color='#8e44ad')
    plt.title('Importancia de Variables - Modelo Final V2 (Validacion Temporal)', fontsize=14)
    plt.xlabel('Importancia Relativa')
    plt.tight_layout()
    fi_path = MODELS_DIR / 'feature_importance_final.png'
    plt.savefig(fi_path, dpi=150)
    plt.close()
    print(f"Feature importance -> {fi_path}")
    
    roc_path = MODELS_DIR / 'roc_curve_final.png'
    plot_roc_curve(y_test, y_prob, roc_path)
    print(f"Curva ROC -> {roc_path}")
    
    cm_path = MODELS_DIR / 'confusion_matrix_final.png'
    plot_confusion_matrix(y_test, y_pred, cm_path)
    print(f"Matriz de confusion -> {cm_path}")
    
    # --- GUARDAR MODELO ---
    model_path = MODELS_DIR / 'xgboost_fire_model_final.pkl'
    joblib.dump(best_model, model_path)
    print(f"\nModelo final guardado -> {model_path}")
    
    # --- GUARDAR METADATOS ---
    metadata = {
        'version': 'V2',
        'train_years': f'{train_df["year"].min()}-{train_df["year"].max()}',
        'test_years': f'{test_df["year"].min()}-{test_df["year"].max()}',
        'train_samples': len(train_df),
        'test_samples': len(test_df),
        'accuracy': acc,
        'f1_score': f1,
        'roc_auc': auc,
        'best_params': best_params,
        'features': features,
        'optuna_trials': OPTUNA_TRIALS,
        'improvements': [
            'Clean test set (only years with both classes)',
            'Climate interaction features (dryness, drought, fire weather)',
            'Sample weights in Optuna CV',
            'Vectorized sample weight computation',
            'Expanded Optuna search (reg_alpha, reg_lambda, n_estimators up to 800)',
        ],
    }
    joblib.dump(metadata, MODELS_DIR / 'model_metadata_final.pkl')


if __name__ == "__main__":
    train_final()
