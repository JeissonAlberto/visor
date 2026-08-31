import subprocess
import unittest
from unittest.mock import patch

from core.lan_vision import (
    MAX_LAN_HOSTS,
    MAX_PORT_WORKERS,
    _get_arp_table,
    _ping_host,
    _scan_ports_fast,
    discover_lan,
)


class _FailingSocket:
    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True
        return False

    def settimeout(self, timeout):
        pass

    def connect_ex(self, address):
        raise OSError("simulated connection failure")


class LanVisionTests(unittest.TestCase):
    def test_port_probe_closes_socket_when_connect_fails(self):
        sock = _FailingSocket()
        with patch("core.lan_vision.socket.socket", return_value=sock):
            self.assertEqual(_scan_ports_fast("192.0.2.1", [443]), [])
        self.assertTrue(sock.closed)

    def test_ping_returns_offline_when_system_command_is_unavailable(self):
        with patch("core.lan_vision.subprocess.run", side_effect=OSError("missing ping")):
            self.assertFalse(_ping_host("192.0.2.1"))

    def test_arp_enrichment_returns_empty_table_when_command_times_out(self):
        with patch(
            "core.lan_vision.subprocess.run",
            side_effect=subprocess.TimeoutExpired("arp", 5),
        ):
            self.assertEqual(_get_arp_table(), {})

    def test_empty_port_list_does_not_create_worker_pool(self):
        with patch("core.lan_vision.concurrent.futures.ThreadPoolExecutor") as executor:
            self.assertEqual(_scan_ports_fast("192.0.2.1", []), [])
        executor.assert_not_called()

    def test_port_probe_caps_worker_pool_for_custom_port_lists(self):
        ports = list(range(1, MAX_PORT_WORKERS * 2 + 1))
        with patch("core.lan_vision.concurrent.futures.ThreadPoolExecutor") as executor:
            _scan_ports_fast("192.0.2.1", ports)
        executor.assert_called_once_with(max_workers=MAX_PORT_WORKERS)

    def test_rejects_oversized_cidr_before_network_probes(self):
        with patch("core.lan_vision._ping_host") as ping:
            with self.assertRaisesRegex(ValueError, "rango LAN demasiado grande"):
                discover_lan("10.0.0.0/8", scan_ports=False)
        ping.assert_not_called()
        self.assertGreater(MAX_LAN_HOSTS, 0)


if __name__ == "__main__":
    unittest.main()
