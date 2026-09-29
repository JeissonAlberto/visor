import unittest

from core.wifi import mikrotik_wifi_clients


class MikrotikWifiClientsTests(unittest.TestCase):
    def test_all_query_failures_are_reported_without_exception_details(self):
        def failing_ssh(*args, **kwargs):
            raise RuntimeError("credential=do-not-leak")

        result = mikrotik_wifi_clients(
            host="192.0.2.10",
            user="test-user",
            password="test-secret",
            ssh_fn=failing_ssh,
        )

        self.assertFalse(result["disponible"])
        self.assertEqual(result["clientes"], [])
        self.assertEqual(
            result["advertencia"],
            "No se pudo consultar la tabla de asociaciones Wi-Fi.",
        )
        self.assertNotIn("do-not-leak", repr(result))
        self.assertNotIn("test-secret", repr(result))

    def test_empty_successful_tables_are_not_misreported_as_query_failures(self):
        result = mikrotik_wifi_clients(
            host="192.0.2.10",
            user="test-user",
            password="test-secret",
            ssh_fn=lambda *args, **kwargs: "",
        )

        self.assertFalse(result["disponible"])
        self.assertEqual(result["clientes"], [])
        self.assertNotIn("advertencia", result)
        self.assertIn("No se encontraron asociaciones activas", result["motivo"])

    def test_error_output_from_all_queries_is_reported(self):
        result = mikrotik_wifi_clients(
            host="192.0.2.10",
            user="test-user",
            password="test-secret",
            ssh_fn=lambda *args, **kwargs: "ERROR: authentication failed",
        )

        self.assertEqual(
            result["advertencia"],
            "No se pudo consultar la tabla de asociaciones Wi-Fi.",
        )
        self.assertNotIn("authentication", repr(result))

    def test_one_supported_registration_table_can_return_clients(self):
        calls = 0

        def ssh(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return "ERROR: unsupported command"
            return "AA:BB:CC:00:00:20|wifi1|-45dBm|100Mbps|80Mbps|1h"

        result = mikrotik_wifi_clients(
            host="192.0.2.10",
            user="test-user",
            password="test-secret",
            ssh_fn=ssh,
        )

        self.assertTrue(result["disponible"])
        self.assertEqual(len(result["clientes"]), 1)
        self.assertEqual(result["clientes"][0]["mac"], "AA:BB:CC:00:00:20")
        self.assertNotIn("advertencia", result)


if __name__ == "__main__":
    unittest.main()
