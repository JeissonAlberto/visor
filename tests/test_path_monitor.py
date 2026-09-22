import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.path_monitor import _atomic_write_text, monitor_once, parse_ping_output, write_live_reports


class PathMonitorTests(unittest.TestCase):
    def test_parses_windows_and_spanish_ping_summary(self):
        output = "Packets: Sent = 3, Received = 3, Lost = 0 (0% loss),\nApproximate round trip times: Minimum = 1ms, Maximum = 4ms, Average = 2ms"
        metric = parse_ping_output(output)
        self.assertEqual(metric["perdida_pct"], 0)
        self.assertEqual(metric["promedio_ms"], 2.0)
        self.assertTrue(metric["alcanzable"])

    def test_parses_accented_spanish_ping_loss(self):
        output = "5 paquetes transmitidos, 5 recibidos, 0% de pérdida de paquetes\nMedia = 3 ms"
        metric = parse_ping_output(output)
        self.assertEqual(metric["perdida_pct"], 0)
        self.assertEqual(metric["promedio_ms"], 3.0)
        self.assertTrue(metric["alcanzable"])

    def test_parses_linux_ping_summary(self):
        output = (
            "3 packets transmitted, 3 received, 0% packet loss, time 2002ms\n"
            "rtt min/avg/max/mdev = 1.120/2.345/4.567/0.500 ms"
        )
        metric = parse_ping_output(output)
        self.assertEqual(metric["perdida_pct"], 0)
        self.assertEqual(metric["promedio_ms"], 2.345)
        self.assertTrue(metric["alcanzable"])

    def test_parses_fractional_loss_and_reachability(self):
        output = "10 packets transmitted, 9 received, 10.0% packet loss\nrtt min/avg/max/mdev = 1/5/9/1 ms"
        metric = parse_ping_output(output)
        self.assertEqual(metric["perdida_pct"], 10)
        self.assertEqual(metric["promedio_ms"], 5.0)
        self.assertTrue(metric["alcanzable"])

    def test_atomic_write_preserves_previous_file_on_replace_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "topology_live.json"
            path.write_text("previous", encoding="utf-8")
            with patch("core.path_monitor.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    _atomic_write_text(path, "new")
            self.assertEqual(path.read_text(encoding="utf-8"), "previous")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_report_writer_keeps_probe_errors_in_new_csv(self):
        topology = {
            "ts": "2026-08-06T16:00:00",
            "nodos": [],
            "conexiones": [],
            "trazas": [],
            "resumen": {},
            "monitorizacion": {"objetivo": "1.1.1.1", "saltos": [{"host": "1.1.1.1", "perdida_pct": 100, "alcanzable": False, "error": "ping no disponible"}]},
        }
        with tempfile.TemporaryDirectory() as directory:
            paths = write_live_reports(topology, Path(directory))
            csv_lines = Path(paths["csv"]).read_text(encoding="utf-8").splitlines()
            self.assertIn("error", csv_lines[0])
            self.assertIn("ping no disponible", csv_lines[1])

    def test_report_writer_ignores_malformed_optional_metrics(self):
        topology = {
            "ts": "2026-08-06T16:00:00",
            "nodos": [],
            "conexiones": [],
            "trazas": [],
            "resumen": {},
            "monitorizacion": {"objetivo": "1.1.1.1", "saltos": [None, "invalid", {"host": "1.1.1.1", "perdida_pct": 0}]},
        }
        with tempfile.TemporaryDirectory() as directory:
            paths = write_live_reports(topology, Path(directory))
            csv_lines = Path(paths["csv"]).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(csv_lines), 2)  # encabezado + única métrica válida
            self.assertIn("1.1.1.1", csv_lines[1])

    def test_monitor_ignores_malformed_traces_and_nodes(self):
        topology = {
            "trazas": [None, {"saltos": "invalid", "ip_destino": "1.1.1.1"}, "invalid"],
            "nodos": [None, "invalid"],
        }
        result = monitor_once(
            "1.1.1.1",
            topology_fn=lambda **kwargs: topology,
            probe_fn=lambda host, count: {"host": host, "perdida_pct": 0, "promedio_ms": 5.0, "alcanzable": True},
        )
        self.assertEqual(result["monitorizacion"]["saltos"][0]["host"], "1.1.1.1")
        self.assertEqual(result["nodos"], [None, "invalid"])

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
            write_live_reports(result, Path(directory))
            self.assertTrue(Path(paths["drawio"]).exists())
            self.assertTrue(Path(paths["csv"]).exists())
            self.assertIn("ICMP", Path(paths["txt"]).read_text(encoding="utf-8"))
            history_lines = Path(paths["history"]).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(history_lines), 2)
            csv_lines = Path(paths["csv"]).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(csv_lines), 3)  # encabezado + una métrica por muestra
            self.assertEqual(sum(line.startswith("ts,") for line in csv_lines), 1)


if __name__ == "__main__":
    unittest.main()
