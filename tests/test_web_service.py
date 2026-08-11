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
        web_service._SSL_CONTEXT_HOSTNAME = None
        context = web_service._ssl_ctx()
        hostname_context = web_service._ssl_ctx(check_hostname=True)

        self.assertFalse(context.check_hostname)
        self.assertTrue(hostname_context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(hostname_context.verify_mode, ssl.CERT_REQUIRED)

    def test_domain_url_uses_hostname_verification(self):
        web_service._SSL_CONTEXT = None
        web_service._SSL_CONTEXT_HOSTNAME = None
        response = Mock(status=200)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        with patch("core.web_service.socket.socket") as socket_factory, patch(
            "core.web_service.urllib.request.urlopen", return_value=response
        ) as urlopen:
            result = verificar_url("https://example.test")

        self.assertTrue(result["online"])
        context = urlopen.call_args.kwargs["context"]
        self.assertTrue(context.check_hostname)
        socket_factory.return_value.connect.assert_called_once_with(("example.test", 443))


if __name__ == "__main__":
    unittest.main()
