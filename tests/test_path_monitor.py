import tempfile
import unittest
from pathlib import Path

from core.path_monitor import monitor_once, parse_ping_output, write_live_reports


class PathMonitorTests(unittest.TestCase):
    def test_parses_windows_and_spanish_ping_summary(self):
        output = "Packets: Sent = 3, Received = 3, Lost = 0 (0% loss),\nApproximate round trip times: Minimum = 1ms, Maximum = 4ms, Average = 2ms"
        metric = parse_ping_output(output)
        self.assertEqual(metric["perdida_pct"], 0)
        self.assertEqual(metric["promedio_ms"], 2.0)
        self.assertTrue(metric["alcanzable"])

    def test_monitor_adds_metrics_and_writes_live_drawio(self):
        topology = {
            "ts": "2026-08-06T16:00:00",
            "nodos": [{"id": "ip:1.1.1.1", "ip": "1.1.1.1", "rol": "route_hop", "tipo": "Salto L3", "evidencia": [], "verificaciones": []}],
            "conexiones": [],
            "trazas": [{"ip_destino": "1.1.1.1", "saltos": [{"ip": "1.1.1.1"}]}],
            "resumen": {"nodos": 1, "equipos_wifi": 0},
        }
        result = monitor_once(
            "1.1.1.1",
            topology_fn=lambda **kwargs: topology,
            probe_fn=lambda host, count: {"host": host, "perdida_pct": 0, "promedio_ms": 8.0, "alcanzable": True},
        )
        self.assertEqual(result["monitorizacion"]["saltos"][0]["promedio_ms"], 8.0)
        with tempfile.TemporaryDirectory() as directory:
            paths = write_live_reports(result, Path(directory))
            self.assertTrue(Path(paths["drawio"]).exists())
            self.assertTrue(Path(paths["csv"]).exists())
            self.assertIn("ICMP", Path(paths["txt"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
