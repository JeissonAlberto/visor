import unittest
from unittest.mock import patch

from core.health import MAX_QUALITY_PROBES, analizar_calidad


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


if __name__ == "__main__":
    unittest.main()
