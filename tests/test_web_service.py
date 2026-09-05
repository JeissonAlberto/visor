import ssl
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

import core.web_service as web_service
from core.web_service import (
    escanear_por_categorias,
    escanear_servicios_web,
    geolocalizacion_ip,
    verificar_url,
)


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

    def test_malformed_url_returns_result_without_network_request(self):
        with patch("core.web_service.socket.socket") as socket_factory, patch(
            "core.web_service.urllib.request.urlopen"
        ) as urlopen:
            result = verificar_url("https://example.test:not-a-port")

        self.assertFalse(result["online"])
        self.assertEqual(result["estado"], "DOWN")
        self.assertIsNone(result["latencia"])
        self.assertIn("URL inválida", result["error"])
        socket_factory.assert_not_called()
        urlopen.assert_not_called()

    def test_unsupported_scheme_returns_result_without_network_request(self):
        with patch("core.web_service.socket.socket") as socket_factory, patch(
            "core.web_service.urllib.request.urlopen"
        ) as urlopen:
            result = verificar_url("ftp://example.test/file")

        self.assertFalse(result["online"])
        self.assertIn("http(s)", result["error"])
        socket_factory.assert_not_called()
        urlopen.assert_not_called()

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

    def test_unexpected_http_error_is_not_hidden(self):
        with patch("core.web_service.socket.socket"), patch(
            "core.web_service.urllib.request.urlopen",
            side_effect=RuntimeError("unexpected test failure"),
        ):
            with self.assertRaises(RuntimeError):
                verificar_url("https://example.test")

    def test_service_scan_ignores_malformed_entries_without_aborting(self):
        with patch("core.web_service.verificar_url", return_value={
            "url": "https://example.test", "online": True
        }) as verify:
            results = escanear_servicios_web([
                None,
                {"nombre": "Sin URL", "url": None},
                {"nombre": "Puerto inválido", "url": 443},
                {"nombre": "Vacío", "url": "  "},
                {"nombre": "Servicio válido", "url": " https://example.test "},
            ])

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["error"], "URL inválida")
        self.assertEqual(results[0]["nombre"], "Puerto inválido")
        verify.assert_called_once_with("https://example.test")

    def test_category_scan_skips_malformed_configured_services(self):
        response = {"url": "https://example.test", "online": True}
        with patch.object(
            web_service,
            "SERVICIOS_WEB",
            [None, {"url": None}, {"url": " https://example.test "}],
        ), patch("core.web_service.verificar_url", return_value=response) as verify:
            categories = escanear_por_categorias()

        self.assertEqual(len(categories["Mis Servicios"]), 1)
        self.assertEqual(categories["Mis Servicios"][0]["url"], "https://example.test")
        verify.assert_any_call("https://example.test")


if __name__ == "__main__":
    unittest.main()
