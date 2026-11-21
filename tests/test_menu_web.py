import contextlib
import io
import unittest
from unittest.mock import patch

from ui.menu import _formatear_latencia, _menu_web


class MenuWebLatencyTests(unittest.TestCase):
    def test_missing_or_invalid_latency_is_not_formatted(self):
        for value in (None, True, "71", float("nan"), float("inf"), -1):
            with self.subTest(value=value):
                self.assertIsNone(_formatear_latencia(value))

    def test_zero_latency_is_a_valid_measurement(self):
        self.assertEqual(_formatear_latencia(0), "0ms")
        self.assertEqual(_formatear_latencia(0.4), "0ms")

    def test_menu_survives_missing_web_latency_and_http_status(self):
        results = {"Test": [{"nombre": "Servicio", "online": True,
                             "latencia": None, "lat_red": 71.0, "http": None}]}
        output = io.StringIO()
        with patch("core.web_service.escanear_por_categorias", return_value=results), \
             patch("utils.reportes.guardar_reporte", return_value=None), \
             patch("builtins.input", return_value=""), \
             contextlib.redirect_stdout(output):
            _menu_web()
        shown = output.getvalue()
        self.assertIn("Red 71ms", shown)
        self.assertIn("HTTP —", shown)
        self.assertNotIn("None", shown)

    def test_menu_formats_both_zero_latencies(self):
        results = {"Test": [{"nombre": "Servicio", "online": True,
                             "latencia": 0, "lat_red": 0, "http": 200}]}
        output = io.StringIO()
        with patch("core.web_service.escanear_por_categorias", return_value=results), \
             patch("utils.reportes.guardar_reporte", return_value=None), \
             patch("builtins.input", return_value=""), \
             contextlib.redirect_stdout(output):
            _menu_web()
        self.assertIn("0ms -> 0ms", output.getvalue())


if __name__ == "__main__":
    unittest.main()
