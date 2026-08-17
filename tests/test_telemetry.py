import json
import unittest
from unittest.mock import Mock, patch

from core.telemetry import TelemetryClient, create_event, topology_event


class TelemetryTests(unittest.TestCase):
    def test_event_schema_and_identifier_redaction(self):
        event = create_event("topology.path_sample", {"ok": True}, observed_at="2026-08-06T00:00:00Z")
        self.assertEqual(event["schema"], "visor.telemetry.v1")
        topology = {"ts": "2026-08-06T00:00:00Z", "monitorizacion": {"objetivo": "8.8.8.8", "saltos": [{"host": "10.0.0.1", "perdida_pct": 0, "promedio_ms": 2.0, "alcanzable": True}]}, "resumen": {"saltos_l3": 1}}
        safe = topology_event(topology)
        self.assertNotIn("8.8.8.8", json.dumps(safe))
        self.assertNotIn("10.0.0.1", json.dumps(safe))

    def test_client_is_opt_in_and_sends_to_test_adapter(self):
        skipped = TelemetryClient(url="http://127.0.0.1:3049/events", enabled=False).send_event({"x": 1})
        self.assertTrue(skipped["skipped"])
        response = Mock(status=202)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        opener = Mock()
        opener.open.return_value = response
        with patch("core.telemetry.urllib.request.build_opener", return_value=opener):
            result = TelemetryClient(url="http://127.0.0.1:3049/events", token="test-token", enabled=True).send_event({"x": 1})
        self.assertTrue(result["sent"])
        request = opener.open.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"x": 1})
        self.assertEqual(request.headers["Authorization"], "Bearer test-token")

    def test_http_endpoint_requires_exact_local_hostname(self):
        opener = Mock()
        with patch("core.telemetry.urllib.request.build_opener", return_value=opener):
            result = TelemetryClient(
                url="http://localhost.evil.example/events", enabled=True
            ).send_event({"x": 1})

        self.assertTrue(result["skipped"])
        opener.open.assert_not_called()

    def test_endpoint_with_embedded_credentials_is_rejected(self):
        result = TelemetryClient(
            url="https://user:password@example.test/events", enabled=True
        ).send_event({"x": 1})

        self.assertTrue(result["skipped"])
        self.assertIn("no permitido", result["reason"])


if __name__ == "__main__":
    unittest.main()
