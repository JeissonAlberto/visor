import unittest
from unittest.mock import patch

from core.monitor import (
    _rango_desde_mascara,
    _rango_desde_rutas,
    _resolver_direccion,
    escanear_dispositivos,
)


class MonitorTests(unittest.TestCase):
    def test_detects_most_specific_connected_route(self):
        routes = """
        default via 192.168.10.1 dev eth0
        192.168.0.0/16 dev eth0 scope link src 192.168.10.42
        192.168.10.0/23 dev eth0 proto kernel scope link src 192.168.10.42
        """
        self.assertEqual(
            _rango_desde_rutas("192.168.10.42", routes), "192.168.10.0/23"
        )

    def test_builds_network_from_windows_subnet_mask(self):
        self.assertEqual(
            _rango_desde_mascara("10.20.3.44", "255.255.255.192"),
            "10.20.3.0/26",
        )
        self.assertIsNone(_rango_desde_mascara("not-an-ip", "255.255.255.0"))

    def test_resolver_ignores_non_text_addresses(self):
        with patch("core.monitor.buscar_ip_por_mac") as by_mac, patch(
            "core.monitor.resolver_host"
        ) as resolve:
            address, method = _resolver_direccion({"ip": 123, "mac": None})

        self.assertIsNone(address)
        self.assertEqual(method, "Sin dirección")
        by_mac.assert_not_called()
        resolve.assert_not_called()

    def test_auto_discovery_does_not_mutate_caller_list(self):
        configured = [{"nombre": "Gateway", "ip": "192.0.2.1"}]
        discovered = [{"nombre": "Host", "ip": "192.0.2.2"}]
        with patch("core.monitor.detectar_red_local", return_value=(
            "192.0.2.10", "192.0.2.1", "192.0.2.0/24"
        )), patch("core.monitor._descubrir_dispositivos_red", return_value=discovered), patch(
            "core.monitor.hacer_ping", return_value=(False, None)
        ):
            results = escanear_dispositivos(configured, auto_descubrir=True)

        self.assertEqual(len(configured), 1)
        self.assertEqual(len(results), 2)
        self.assertEqual([r["ip"] for r in results], ["192.0.2.1", "192.0.2.2"])

    def test_malformed_device_entries_are_skipped(self):
        with patch("core.monitor.detectar_red_local", return_value=(
            "127.0.0.1", None, "192.168.1.0/24"
        )), patch("core.monitor.hacer_ping", return_value=(False, None)):
            results = escanear_dispositivos(
                [None, {"ip": 123, "mac": None}], auto_descubrir=False
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metodo"], "Sin dirección")


if __name__ == "__main__":
    unittest.main()
