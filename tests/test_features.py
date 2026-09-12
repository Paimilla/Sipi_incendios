"""
Pruebas Unitarias — Feature Engineering (SIpi Incendios)
========================================================
Valida la consistencia de las 22 variables del modelo,
cálculo de índices climáticos y encoding temporal.
"""
import unittest
import numpy as np
import pandas as pd
from datetime import datetime

# Definición de fórmulas de features
def compute_climate_interactions(temp_max, temp_mean, humidity_min, humidity_mean, precip_acc, wind_speed_max):
    dryness = temp_max * (100 - humidity_mean) / 100
    drought = 1 if precip_acc < 1.0 else 0
    ratio = temp_max / (humidity_min + 1)
    fwi = temp_max * wind_speed_max / (humidity_min + 1)
    return {
        'dryness_index': dryness,
        'precip_drought': drought,
        'temp_humidity_ratio': ratio,
        'fire_weather_index': fwi
    }

def compute_temporal(date_str):
    target_date = datetime.strptime(date_str, '%Y-%m-%d')
    m = target_date.month
    doy = target_date.timetuple().tm_yday
    
    def get_season(month):
        if month in [12, 1, 2, 3]: return 1
        elif month in [4, 5]: return 2
        elif month in [6, 7, 8]: return 3
        else: return 4

    return {
        'month_sin': np.sin(2 * np.pi * m / 12),
        'month_cos': np.cos(2 * np.pi * m / 12),
        'day_of_year': doy,
        'season': get_season(m)
    }


class TestFeatureEngineering(unittest.TestCase):

    def test_dryness_index_calculation(self):
        """Verifica que el índice de sequedad aumente con temperatura y baje con humedad."""
        # Caso 1: Calor y aire seco
        res1 = compute_climate_interactions(35.0, 25.0, 15.0, 30.0, 0.0, 20.0)
        # Caso 2: Frío y aire húmedo
        res2 = compute_climate_interactions(10.0, 8.0, 70.0, 85.0, 15.0, 5.0)
        
        self.assertGreater(res1['dryness_index'], res2['dryness_index'])
        self.assertAlmostEqual(res1['dryness_index'], 35.0 * 0.70, places=4)

    def test_drought_binary_indicator(self):
        """Verifica que precipitación < 1.0mm active la bandera de sequía."""
        res_drought = compute_climate_interactions(30.0, 20.0, 20.0, 40.0, 0.5, 10.0)
        res_rain = compute_climate_interactions(30.0, 20.0, 20.0, 40.0, 15.0, 10.0)
        
        self.assertEqual(res_drought['precip_drought'], 1)
        self.assertEqual(res_rain['precip_drought'], 0)

    def test_fire_weather_index_sensitivity(self):
        """Verifica que el FWI aumente fuertemente con viento y calor."""
        calm = compute_climate_interactions(30.0, 20.0, 20.0, 40.0, 0.0, 5.0)
        windy = compute_climate_interactions(30.0, 20.0, 20.0, 40.0, 0.0, 35.0)
        
        self.assertGreater(windy['fire_weather_index'], calm['fire_weather_index'])

    def test_cyclical_month_encoding(self):
        """Verifica que diciembre (mes 12) y enero (mes 1) estén cercanos en el espacio cíclico."""
        dec = compute_temporal('2023-12-15')
        jan = compute_temporal('2024-01-15')
        jul = compute_temporal('2023-07-15')
        
        dist_dec_jan = np.sqrt((dec['month_sin'] - jan['month_sin'])**2 + (dec['month_cos'] - jan['month_cos'])**2)
        dist_jan_jul = np.sqrt((jan['month_sin'] - jul['month_sin'])**2 + (jan['month_cos'] - jul['month_cos'])**2)
        
        self.assertLess(dist_dec_jan, dist_jan_jul)
        self.assertEqual(jan['season'], 1) # Verano
        self.assertEqual(jul['season'], 3) # Invierno


if __name__ == '__main__':
    unittest.main()
