import ssl
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

import core.web_service as web_service
from core.web_service import geolocalizacion_ip, verificar_url


class WebServiceTests(unittest.TestCase):
    def test_invalid_ip_is_rejected_without_external_request(self):
        with patch("core.web_service.urllib.request.urlopen") as urlopen:
            result = geolocalizacion_ip("not-an-ip")

        self.assertEqual(result, {"ip": "not-an-ip", "privada": False, "error": "IP inválida"})
        urlopen.assert_not_called()

    def test_non_global_ipv6_is_not_sent_to_geolocation_provider(self):
        with patch("core.web_service.urllib.request.urlopen") as urlopen:
            result = geolocalizacion_ip("fd00::1")

        self.assertTrue(result["privada"])
        self.assertIn("sin geolocalización", result["info"])
        urlopen.assert_not_called()

    def test_failed_tcp_connect_closes_socket(self):
        sock = Mock()
        sock.connect.side_effect = OSError("connection refused")
        with patch("core.web_service.socket.socket", return_value=sock), patch(
            "core.web_service.urllib.request.urlopen",
            side_effect=URLError("web unavailable"),
        ):
            result = verificar_url("http://example.test", timeout=1)

        self.assertFalse(result["online"])
        sock.close.assert_called_once_with()

    def test_https_context_verifies_certificate_chain(self):
        web_service._SSL_CONTEXT = None
        context = web_service._ssl_ctx()

        self.assertFalse(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)


if __name__ == "__main__":
    unittest.main()
