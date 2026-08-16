import inspect
import ssl
import unittest
from unittest.mock import patch

from core.test_internet import _medir_throughput_tcp, _ssl_ctx


class InternetSecurityTests(unittest.TestCase):
    def test_speed_test_context_verifies_certificates_and_hostnames(self):
        context = _ssl_ctx()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_loopback_throughput_uses_ephemeral_port(self):
        source = inspect.getsource(_medir_throughput_tcp)

        self.assertIn('srv.bind(("127.0.0.1", 0))', source)
        self.assertNotIn("PUERTO = 54321", source)

    def test_loopback_start_failure_is_reported_without_client_connection(self):
        with patch("core.test_internet.socket.socket", side_effect=OSError("loopback blocked")):
            mbps, detail = _medir_throughput_tcp()

        self.assertIsNone(mbps)
        self.assertEqual(detail, "loopback blocked")


if __name__ == "__main__":
    unittest.main()
