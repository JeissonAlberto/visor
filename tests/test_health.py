import subprocess
import unittest
from unittest.mock import patch

from core.health import MAX_QUALITY_PROBES, MAX_TRACE_HOPS, analizar_calidad, traceroute


class HealthTests(unittest.TestCase):
    def test_rejects_invalid_probe_count_before_network_calls(self):
        for invalid in (0, -1, MAX_QUALITY_PROBES + 1, True, "not-a-number"):
            with self.subTest(rafagas=invalid), patch("core.health.hacer_ping") as ping:
                with self.assertRaises(ValueError):
                    analizar_calidad("192.0.2.1", invalid)
            ping.assert_not_called()

    def test_one_probe_returns_offline_report_without_division_error(self):
        with patch("core.health.hacer_ping", return_value=(False, None)), patch(
            "core.health.time.sleep"
        ):
            result = analizar_calidad("192.0.2.1", 1)

        self.assertEqual(result["estado"], "OFFLINE")
        self.assertEqual(result["loss"], 100)

    def test_traceroute_rejects_oversized_hop_limit_before_running_command(self):
        with patch("core.health.subprocess.run") as run:
            with self.assertRaises(ValueError):
                traceroute("192.0.2.1", MAX_TRACE_HOPS + 1)
        run.assert_not_called()

    def test_traceroute_reports_expected_system_errors(self):
        with patch("core.health.platform.system", return_value="Linux"), patch(
            "core.health.subprocess.run", side_effect=subprocess.TimeoutExpired("traceroute", 60)
        ):
            result = traceroute("192.0.2.1", 7)

        self.assertEqual(result[0]["ip"], "error")
        self.assertTrue(result[0]["timeout"])

    def test_traceroute_does_not_hide_unexpected_errors(self):
        with patch("core.health.platform.system", return_value="Linux"), patch(
            "core.health.subprocess.run", side_effect=RuntimeError("unexpected")
        ):
            with self.assertRaises(RuntimeError):
                traceroute("192.0.2.1", 7)

    def test_traceroute_passes_valid_hop_limit_to_system_command(self):
        completed = type("Completed", (), {"stdout": "", "returncode": 0})()
        with patch("core.health.platform.system", return_value="Linux"), patch(
            "core.health.subprocess.run", return_value=completed
        ) as run:
            self.assertEqual(traceroute("192.0.2.1", 7), [])

        self.assertEqual(run.call_args.args[0], [
            "traceroute", "-n", "-m", "7", "-w", "2", "192.0.2.1"
        ])


if __name__ == "__main__":
    unittest.main()
