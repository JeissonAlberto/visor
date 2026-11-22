import inspect
import ssl
import unittest
from unittest.mock import patch

from core.test_internet import _medir_subida, _medir_throughput_tcp, _ping_latencias, _ssl_ctx


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
