import socket
import subprocess
import unittest
from unittest.mock import patch

from core.red import MAX_SCAN_HOSTS, detectar_gateway, escanear_rango, hacer_ping


class RangeScanTests(unittest.TestCase):
    def test_ping_rejects_option_like_destinations_before_running_command(self):
        for host in ("-f", "/t", "", "   ", None):
            with self.subTest(host=host), patch("core.red.subprocess.run") as run:
                self.assertEqual(hacer_ping(host), (False, None))
            run.assert_not_called()

    def test_ping_returns_offline_when_system_command_is_unavailable(self):
        with patch("core.red.subprocess.run", side_effect=OSError("missing ping")):
            self.assertEqual(hacer_ping("192.0.2.1"), (False, None))

    def test_gateway_detection_commands_have_a_five_second_timeout(self):
        cases = (
            ("Windows", ["ipconfig"], "Default Gateway . . . : 192.0.2.1", "192.0.2.1"),
            ("Linux", ["ip", "route"], "default via 192.0.2.254 dev eth0", "192.0.2.254"),
        )
        for system, command, output, expected_gateway in cases:
            with self.subTest(system=system), patch("core.red.platform.system", return_value=system), patch(
                "core.red.subprocess.run",
                return_value=subprocess.CompletedProcess(command, 0, stdout=output, stderr=""),
            ) as run:
                self.assertEqual(detectar_gateway(), expected_gateway)
            run.assert_called_once_with(command, capture_output=True, text=True, timeout=5)

    def test_gateway_detection_returns_none_when_command_times_out(self):
        with patch("core.red.platform.system", return_value="Linux"), patch(
            "core.red.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["ip", "route"], 5),
        ) as run:
            self.assertIsNone(detectar_gateway())
        run.assert_called_once_with(["ip", "route"], capture_output=True, text=True, timeout=5)

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

    def test_zero_latency_is_preserved_for_active_host(self):
        with patch("core.red.hacer_ping", return_value=(True, 0.0)):
            results = escanear_rango("192.0.2.0/31")

        self.assertTrue(all(result["activo"] for result in results))
        self.assertTrue(all(result["latencia"] == 0.0 for result in results))

    def test_reverse_dns_failure_does_not_discard_active_host(self):
        with patch("core.red.hacer_ping", return_value=(True, 4.2)), patch(
            "core.red.socket.gethostbyaddr", side_effect=socket.gaierror
        ):
            results = escanear_rango("192.0.2.0/31")

        self.assertEqual([result["ip"] for result in results], [
            "192.0.2.0", "192.0.2.1"
        ])
        self.assertTrue(all(result["activo"] for result in results))
        self.assertTrue(all(result["hostname"] is None for result in results))

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
