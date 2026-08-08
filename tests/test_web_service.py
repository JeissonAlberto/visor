import unittest
from unittest.mock import patch

from core.web_service import geolocalizacion_ip


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


if __name__ == "__main__":
    unittest.main()
