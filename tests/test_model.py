"""
Pruebas del Modelo XGBoost — SIpi Incendios
===========================================
Valida la carga del artefacto .pkl, consistencia de inferencia,
rango de probabilidades y explicabilidad SHAP.
"""
import unittest
import joblib
from pathlib import Path
import pandas as pd
import numpy as np
import shap

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "src" / "models"

class TestModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        model_path = MODELS_DIR / "xgboost_fire_model_final.pkl"
        meta_path = MODELS_DIR / "model_metadata_final.pkl"
        
        assert model_path.exists(), f"No se encontró el modelo en {model_path}"
        assert meta_path.exists(), f"No se encontró metadata en {meta_path}"
        
        cls.model = joblib.load(model_path)
        cls.metadata = joblib.load(meta_path)
        cls.features = cls.metadata['features']
        cls.explainer = shap.TreeExplainer(cls.model)

    def test_model_metadata_keys(self):
        """Verifica que los metadatos contengan todas las llaves esperadas."""
        self.assertIn('version', self.metadata)
        self.assertIn('features', self.metadata)
        self.assertIn('roc_auc', self.metadata)
        self.assertIn('f1_score', self.metadata)
        self.assertEqual(len(self.features), 22)

    def test_model_prediction_range(self):
        """Verifica que la probabilidad de predicción esté en el rango [0.0, 1.0]."""
        # Crear muestra sintética representativa
        sample_dict = {f: 0.0 for f in self.features}
        sample_dict.update({
            'temp_max_window': 32.0,
            'temp_mean_window': 24.0,
            'humidity_min_window': 18.0,
            'humidity_mean_window': 35.0,
            'precip_acc_window': 0.0,
            'wind_speed_max_window': 25.0,
            'wind_speed_mean_window': 12.0,
            'soil_temp_mean': 22.0,
            'soil_moisture_mean': 0.15,
            'land_cover_class': 9,
            'dist_nearest_town_km': 1.5,
            'elevation': 150.0,
            'slope_deg': 12.0,
            'aspect_deg': 180.0,
            'month_sin': 0.5,
            'month_cos': 0.866,
            'day_of_year': 30,
            'season': 1,
            'dryness_index': 32.0 * 0.65,
            'precip_drought': 1,
            'temp_humidity_ratio': 32.0 / 19.0,
            'fire_weather_index': 32.0 * 25.0 / 19.0
        })
        
        df = pd.DataFrame([sample_dict])[self.features]
        df['land_cover_class'] = df['land_cover_class'].astype('category')
        
        prob = self.model.predict_proba(df)[:, 1][0]
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_shap_explanation_consistency(self):
        """Verifica que el explicador SHAP retorne valores para las 22 variables."""
        sample_dict = {f: 1.0 for f in self.features}
        sample_dict['land_cover_class'] = 9
        
        df = pd.DataFrame([sample_dict])[self.features]
        df['land_cover_class'] = df['land_cover_class'].astype('category')
        
        shap_vals = self.explainer.shap_values(df)[0]
        self.assertEqual(len(shap_vals), 22)
        self.assertTrue(all(np.isfinite(shap_vals)))


if __name__ == '__main__':
    unittest.main()
