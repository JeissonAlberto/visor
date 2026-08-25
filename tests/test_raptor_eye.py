import unittest
from unittest.mock import patch

from core.raptor_eye import MAX_THREAT_HOSTS, _grab_banner, _threat_scan_hosts


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

    def connect(self, address):
        pass

    def send(self, payload):
        pass

    def recv(self, size):
        raise OSError("simulated receive failure")


class RaptorEyeTests(unittest.TestCase):
    def test_threat_scan_accepts_prefix_and_cidr(self):
        self.assertEqual(
            _threat_scan_hosts("192.168.50", 2),
            ["192.168.50.1", "192.168.50.2"],
        )
        self.assertEqual(
            _threat_scan_hosts("192.168.50.0/30", 10),
            ["192.168.50.1", "192.168.50.2"],
        )

    def test_threat_scan_rejects_invalid_or_oversized_input(self):
        with self.assertRaises(ValueError):
            _threat_scan_hosts("192.168.50", -1)
        with self.assertRaises(ValueError):
            _threat_scan_hosts("192.168.50", MAX_THREAT_HOSTS + 1)
        with self.assertRaises(ValueError):
            _threat_scan_hosts("not-an-ip", 1)
        with self.assertRaises(ValueError):
            _threat_scan_hosts("2001:db8::/64", 1)

    def test_banner_probe_closes_socket_when_receive_fails(self):
        sock = _FailingSocket()
        with patch("core.raptor_eye.socket.socket", return_value=sock):
            self.assertEqual(_grab_banner("192.0.2.1", 80), "")
        self.assertTrue(sock.closed)

    def test_lan_investigation_uses_existing_banner_probe(self):
        # The menu previously imported _grab_banner from core.lan_vision,
        # where it does not exist; exercise the early offline path to verify
        # the command can load its dependencies without touching the network.
        with patch("builtins.input", side_effect=["192.0.2.1", ""]), \
             patch("ui.menu_lan_vision.socket.gethostbyname", return_value="192.0.2.1"), \
             patch("core.red.hacer_ping", return_value=(False, None)):
            from ui.menu_lan_vision import _investigar_host
            _investigar_host()


if __name__ == "__main__":
    unittest.main()
