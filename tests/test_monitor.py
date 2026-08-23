import unittest
from unittest.mock import patch

from core.monitor import _resolver_direccion, escanear_dispositivos


class MonitorTests(unittest.TestCase):
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
