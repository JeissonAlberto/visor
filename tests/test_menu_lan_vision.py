import io
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ui.menu_lan_vision import _ip_sort_key, _mapa_visual


class LanVisionMenuTests(unittest.TestCase):
    def test_ip_sort_key_orders_valid_ipv4_parts(self):
        self.assertLess(_ip_sort_key("192.168.1.2"), _ip_sort_key("192.168.1.10"))

    def test_ip_sort_key_handles_malformed_values(self):
        self.assertEqual(_ip_sort_key(None), (0, 0, 0, 0))
        self.assertEqual(_ip_sort_key("not-an-ip"), (0, 0, 0, 0))

    def test_map_uses_bounded_timeout_for_gateway_lookup(self):
        host = {"ip": "192.0.2.10", "tipo": "host"}
        with (
            patch("core.lan_vision.discover_lan", return_value=[host]),
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run", return_value=SimpleNamespace(stdout="")) as run,
            patch("builtins.input"),
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            _mapa_visual()
        run.assert_called_once_with(
            ["ip", "route"], capture_output=True, text=True, timeout=5
        )

    def test_map_handles_gateway_lookup_timeout(self):
        host = {"ip": "192.0.2.10", "tipo": "host"}
        with (
            patch("core.lan_vision.discover_lan", return_value=[host]),
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ip", 5)) as run,
            patch("builtins.input"),
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            _mapa_visual()
        run.assert_called_once_with(
            ["ip", "route"], capture_output=True, text=True, timeout=5
        )


if __name__ == "__main__":
    unittest.main()
