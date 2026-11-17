import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import database


class DatabaseTests(unittest.TestCase):
    def test_saves_session_and_vulnerabilities_together(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            database, "DB_PATH", Path(directory) / "visor.db"
        ):
            database.inicializar_db()
            session_id = database.guardar_sesion_seguridad(
                "192.0.2.5",
                {
                    "fecha": "2026-11-17T12:00:00",
                    "riesgo_general": "medio",
                    "total_abiertos": 1,
                    "puertos_abiertos": [
                        {"puerto": 443, "servicio": "https", "riesgo": "bajo", "descripcion": "TLS"}
                    ],
                },
            )

            history = database.obtener_historial_reciente()
            self.assertEqual(history[0][0], session_id)
            self.assertEqual(history[0][2], "192.0.2.5")

    def test_failed_vulnerability_insert_rolls_back_session(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            database, "DB_PATH", Path(directory) / "visor.db"
        ):
            database.inicializar_db()
            audit = {
                "fecha": "2026-11-17T12:00:00",
                "riesgo_general": "medio",
                "total_abiertos": 1,
                "puertos_abiertos": [
                    {"puerto": 443, "servicio": "https", "riesgo": "bajo", "descripcion": "TLS"},
                    {"puerto": 22},
                ],
            }

            with self.assertRaises(KeyError):
                database.guardar_sesion_seguridad("192.0.2.5", audit)

            self.assertEqual(database.obtener_historial_reciente(), [])


if __name__ == "__main__":
    unittest.main()
