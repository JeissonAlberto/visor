import unittest
from unittest.mock import patch

from core.security import MAX_AUDIT_PORTS, _normalizar_puertos, auditoria_completa


class SecurityAuditTests(unittest.TestCase):
    def test_filters_invalid_and_duplicate_ports(self):
        with patch("core.security.escanear_puerto", return_value=None) as scan:
            result = auditoria_completa(
                "192.0.2.1", [0, -1, 65536, "not-a-port", True, 443, 443]
            )

        self.assertEqual(result["total_abiertos"], 0)
        scan.assert_called_once_with("192.0.2.1", 443)

    def test_caps_large_port_list_before_creating_tasks(self):
        requested = list(range(1, MAX_AUDIT_PORTS + 500))
        normalized = _normalizar_puertos(requested)

        self.assertEqual(len(normalized), MAX_AUDIT_PORTS)
        self.assertEqual(normalized[-1], MAX_AUDIT_PORTS)

    def test_audit_processes_ports_in_bounded_batches(self):
        with patch("core.security.escanear_puerto", return_value=None) as scan:
            auditoria_completa("192.0.2.1", range(1, 80))

        self.assertEqual(scan.call_count, 79)

    def test_empty_valid_port_list_returns_empty_report(self):
        with patch("core.security.escanear_puerto") as scan:
            result = auditoria_completa("192.0.2.1", [0, "invalid"])

        self.assertEqual(result["puertos_abiertos"], [])
        scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
