import unittest
from unittest.mock import Mock, patch

from ui.menu import _es_privada, _obtener_ip_publica, _PUBLIC_IP_RESPONSE_LIMIT


class MenuHelperTests(unittest.TestCase):
    def test_es_privada_classifies_private_and_public_addresses(self):
        self.assertTrue(_es_privada("192.168.1.20"))
        self.assertFalse(_es_privada("8.8.8.8"))

    def test_es_privada_treats_invalid_input_as_private(self):
        self.assertTrue(_es_privada("not-an-ip"))
        self.assertTrue(_es_privada(None))

    def test_public_ip_fetch_is_size_bounded_and_validates_ip(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        response.read.return_value = b"8.8.8.8\n"
        with patch("ui.menu.urllib.request.urlopen", return_value=response) as urlopen:
            self.assertEqual(_obtener_ip_publica(), "8.8.8.8")

        response.read.assert_called_once_with(_PUBLIC_IP_RESPONSE_LIMIT + 1)
        urlopen.assert_called_once_with("https://api.ipify.org", timeout=5)

    def test_public_ip_fetch_rejects_oversized_response(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        response.read.return_value = b"8" * (_PUBLIC_IP_RESPONSE_LIMIT + 1)
        with patch("ui.menu.urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "demasiado grande"):
                _obtener_ip_publica()

    def test_public_ip_fetch_rejects_malformed_or_non_global_values(self):
        for payload in (b"\x1b[31m8.8.8.8", b"192.168.1.1"):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=None)
            response.read.return_value = payload
            with self.subTest(payload=payload), patch(
                "ui.menu.urllib.request.urlopen", return_value=response
            ):
                with self.assertRaises(ValueError):
                    _obtener_ip_publica()


if __name__ == "__main__":
    unittest.main()
