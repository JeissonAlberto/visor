import unittest
from unittest.mock import patch

from core.red import MAX_SCAN_HOSTS, escanear_rango, hacer_ping


class RangeScanTests(unittest.TestCase):
    def test_ping_returns_offline_when_system_command_is_unavailable(self):
        with patch("core.red.subprocess.run", side_effect=OSError("missing ping")):
            self.assertEqual(hacer_ping("192.0.2.1"), (False, None))

    def test_rejects_oversized_range_before_network_probes(self):
        with patch("core.red.hacer_ping") as ping:
            with self.assertRaisesRegex(ValueError, "rango demasiado grande"):
                escanear_rango("10.0.0.0/8")

        ping.assert_not_called()

    def test_accepts_small_networks_and_clamps_invalid_worker_count(self):
        with patch("core.red.hacer_ping", return_value=(False, None)) as ping:
            results = escanear_rango("192.0.2.0/30", max_workers=0)

        self.assertEqual(len(results), 2)
        self.assertEqual(ping.call_count, 2)

    def test_ipv4_boundary_networks_count_hosts_correctly(self):
        with patch("core.red.hacer_ping", return_value=(False, None)) as ping:
            results = escanear_rango("192.0.2.0/31")

        self.assertEqual(len(results), 2)
        self.assertEqual(ping.call_count, 2)
        self.assertGreater(MAX_SCAN_HOSTS, 0)

    def test_active_ipv6_hosts_are_sorted_without_crashing(self):
        with patch("core.red.hacer_ping", return_value=(True, 1.0)):
            results = escanear_rango("2001:db8::/126")

        self.assertEqual([result["ip"] for result in results], [
            "2001:db8::1", "2001:db8::2", "2001:db8::3"
        ])


if __name__ == "__main__":
    unittest.main()
