import inspect
import ssl
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.test_internet import (
    _medir_con_speedtest, _medir_subida, _medir_throughput_tcp,
    _ping_latencias, _ssl_ctx,
)


class InternetSecurityTests(unittest.TestCase):
    def test_upload_throughput_does_not_read_or_time_response_body(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, *_args, **_kwargs):
                raise AssertionError("response body should not affect upload timing")

        with (
            patch("core.test_internet._UPLOAD_ENDPOINTS", [("test", "https://example.test", "POST", 2)]),
            patch("core.test_internet._ssl_ctx"),
            patch("core.test_internet.urllib.request.urlopen", return_value=Response()),
            patch("core.test_internet.time.perf_counter", side_effect=[10.0, 11.0]),
        ):
            mbps, source = _medir_subida()

        self.assertEqual(mbps, 0.0)  # 2 bytes over 1 second, rounded to 2 decimals
        self.assertEqual(source, "test")

    def test_speed_test_context_verifies_certificates_and_hostnames(self):
        context = _ssl_ctx()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_speedtest_parses_finite_nonnegative_metrics(self):
        result = SimpleNamespace(
            returncode=0,
            stdout='{"download": 12500000, "upload": 2500000, "server": {"name": "NOC test"}}',
        )
        with patch("shutil.which", side_effect=lambda name: "/usr/bin/speedtest" if name == "speedtest" else None), patch(
            "subprocess.run", return_value=result
        ):
            self.assertEqual(_medir_con_speedtest(), (12.5, 2.5, "NOC test"))

    def test_speedtest_rejects_invalid_metrics(self):
        payloads = (
            '{"download": NaN, "upload": 1}',
            '{"download": -1, "upload": 1}',
            '{"download": true, "upload": 1}',
        )
        for payload in payloads:
            with self.subTest(payload=payload), patch(
                "shutil.which", side_effect=lambda name: "/usr/bin/speedtest" if name == "speedtest" else None
            ), patch("subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=payload)):
                self.assertEqual(_medir_con_speedtest(), (None, None, "Respuesta inválida de speedtest-cli"))

    def test_speedtest_uses_safe_default_for_malformed_optional_server(self):
        payload = '{"download": 1000000, "upload": 500000, "server": null}'
        with patch(
            "shutil.which", side_effect=lambda name: "/usr/bin/speedtest" if name == "speedtest" else None
        ), patch("subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=payload)):
            self.assertEqual(_medir_con_speedtest(), (1.0, 0.5, "Speedtest.net"))

    def test_speedtest_failure_does_not_echo_exception_details(self):
        secret_detail = "token=do-not-display"
        with patch("shutil.which", side_effect=lambda name: "/usr/bin/speedtest" if name == "speedtest" else None), patch(
            "subprocess.run", side_effect=OSError(secret_detail)
        ):
            result = _medir_con_speedtest()

        self.assertEqual(result, (None, None, "No se pudo ejecutar speedtest-cli"))
        self.assertNotIn(secret_detail, repr(result))

    def test_unexpected_ping_failure_is_not_hidden(self):
        with patch("core.test_internet.subprocess.run", side_effect=RuntimeError("unexpected test failure")):
            with self.assertRaises(RuntimeError):
                _ping_latencias("example.test")

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
