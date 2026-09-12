"""
Pruebas de Integración — Servidor API Flask (SIpi Incendios)
============================================================
Valida todos los endpoints HTTP del servidor:
  - GET / (Página principal HTML)
  - GET /api/model-info (Metadata y métricas)
  - GET /api/historical-hotspots (Focos históricos)
  - GET /api/evaluation-plots (Lista de gráficos diagnósticos)
  - POST /api/simulate (Simulador de escenarios What-If)
  - Manejo de errores 400 (Coordenadas y fechas inválidas)
"""
import unittest
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from dashboard.server import app

class TestServerAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_get_index_html(self):
        """Verifica que el root '/' retorne el HTML del dashboard con código 200."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'SIpi', res.data)
        self.assertIn(b'Incendios', res.data)

    def test_get_model_info(self):
        """Verifica el endpoint /api/model-info y su estructura JSON."""
        res = self.client.get('/api/model-info')
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertEqual(data.get('version'), 'V2')
        self.assertEqual(data.get('n_features'), 22)
        self.assertIn('metrics', data)
        self.assertIn('roc_auc', data['metrics'])

    def test_get_historical_hotspots(self):
        """Verifica que el endpoint /api/historical-hotspots entregue focos georreferenciados."""
        res = self.client.get('/api/historical-hotspots')
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertGreater(data.get('count', 0), 100)
        self.assertTrue(len(data.get('hotspots', [])) > 100)
        
        # Validar estructura del primer foco
        first = data['hotspots'][0]
        self.assertIn('lat', first)
        self.assertIn('lon', first)
        self.assertIn('ha', first)

    def test_get_evaluation_plots(self):
        """Verifica que el endpoint /api/evaluation-plots liste los gráficos PNG."""
        res = self.client.get('/api/evaluation-plots')
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertIn('plots', data)
        self.assertGreaterEqual(len(data['plots']), 5)

    def test_post_simulate(self):
        """Verifica el endpoint del simulador climático /api/simulate."""
        payload = {
            'lat': -36.82,
            'lon': -73.05,
            'fecha': '2023-02-03',
            'delta_temp': 5.0,
            'delta_humidity': -15.0,
            'delta_wind': 10.0
        }
        res = self.client.post('/api/simulate', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertIn('baseline', data)
        self.assertIn('simulated', data)
        self.assertIn('delta_probability', data)
        self.assertIn('shap_factors', data)
        self.assertIn(data['simulated']['risk_level'], ['Bajo', 'Moderado', 'Alto', 'Crítico', 'Nulo'])

    def test_predict_validation_errors(self):
        """Verifica que coordenadas fuera de Chile retornen código 400."""
        # Latitud fuera de Chile
        res_lat = self.client.post('/api/predict', json={'lat': 10.0, 'lon': -70.0, 'fecha': '2024-01-15'})
        self.assertEqual(res_lat.status_code, 400)
        
        # Longitud fuera de Chile
        res_lon = self.client.post('/api/predict', json={'lat': -33.0, 'lon': -10.0, 'fecha': '2024-01-15'})
        self.assertEqual(res_lon.status_code, 400)
        
        # Fecha inválida
        res_date = self.client.post('/api/predict', json={'lat': -33.0, 'lon': -70.0, 'fecha': 'fecha-invalida'})
        self.assertEqual(res_date.status_code, 400)

    def test_get_search_places(self):
        """Verifica que el endpoint de búsqueda de comunas /api/search-places retorne coincidencias."""
        res = self.client.get('/api/search-places?q=Chillan')
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertIn('results', data)
        self.assertGreater(len(data['results']), 0)
        first = data['results'][0]
        self.assertIn('name', first)
        self.assertIn('lat', first)
        self.assertIn('lon', first)

    def test_get_regional_risk_summary(self):
        """Verifica que /api/regional-risk-summary retorne las 16 regiones de Chile."""
        res = self.client.get('/api/regional-risk-summary')
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertEqual(data.get('total_regions'), 16)
        self.assertEqual(len(data.get('regions', [])), 16)
        
        # Verificar que Biobío y Maule tengan focos históricos registrados
        biobio = next((r for r in data['regions'] if r['name'] == 'Biobío'), None)
        self.assertIsNotNone(biobio)
        self.assertGreater(biobio['historical_hotspots'], 50)

    def test_export_report_formats(self):
        """Verifica la generación de informes técnicos en HTML, JSON y CSV."""
        # 1. JSON
        res_json = self.client.get('/api/export-report?lat=-36.8270&lon=-73.0503&fecha=2023-02-03&format=json')
        self.assertEqual(res_json.status_code, 200)
        self.assertIn('report_title', res_json.json)
        self.assertIn('evaluation', res_json.json)

        # 2. CSV
        res_csv = self.client.get('/api/export-report?lat=-36.8270&lon=-73.0503&fecha=2023-02-03&format=csv')
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn(b'probabilidad,nivel_riesgo', res_csv.data)

        # 3. HTML Printable
        res_html = self.client.get('/api/export-report?lat=-36.8270&lon=-73.0503&fecha=2023-02-03&format=html')
        self.assertEqual(res_html.status_code, 200)
        self.assertIn(b'SIpi Incendios', res_html.data)
        self.assertIn(b'Dossier', res_html.data)

    def test_non_burnable_surfaces(self):
        """Verifica que cuerpos de agua o glaciares retornen 0.0% de probabilidad (Riesgo Nulo)."""
        # Fiordo en Magallanes (Cuerpo de agua)
        res = self.client.post('/api/predict', json={'lat': -50.9679, 'lon': -75.0759, 'fecha': '2015-01-27'})
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertEqual(data['probability'], 0.0)
        self.assertEqual(data['risk_level'], 'Nulo')


if __name__ == '__main__':
    unittest.main()
