import json
import unittest
from unittest.mock import Mock, patch

from core.telemetry import TelemetryClient, _NoRedirectHandler, create_event, topology_event


class TelemetryTests(unittest.TestCase):
    def test_event_schema_and_identifier_redaction(self):
        event = create_event("topology.path_sample", {"ok": True}, observed_at="2026-08-06T00:00:00Z")
        self.assertEqual(event["schema"], "visor.telemetry.v1")
        topology = {"ts": "2026-08-06T00:00:00Z", "monitorizacion": {"objetivo": "8.8.8.8", "saltos": [{"host": "10.0.0.1", "perdida_pct": 0, "promedio_ms": 2.0, "alcanzable": True}]}, "resumen": {"saltos_l3": 1}}
        safe = topology_event(topology)
        self.assertNotIn("8.8.8.8", json.dumps(safe))
        self.assertNotIn("10.0.0.1", json.dumps(safe))

    def test_topology_event_limits_summary_to_nonnegative_aggregate_counters(self):
        event = topology_event({"resumen": {
            "nodos": 3,
            "conexiones_verificadas": 2,
            "objetivo": "10.0.0.1",
            "host": "router-secret",
            "malicious": {"token": "secret"},
            "equipos_lan": -1,
            "saltos_l3": True,
        }})

        self.assertEqual(event["payload"]["resumen"], {
            "nodos": 3, "conexiones_verificadas": 2,
        })
        encoded = json.dumps(event)
        self.assertNotIn("10.0.0.1", encoded)
        self.assertNotIn("router-secret", encoded)
        self.assertNotIn("secret", encoded)

    def test_topology_event_filters_invalid_numeric_metrics(self):
        topology = {"monitorizacion": {"saltos": [
            {"host": "router", "perdida_pct": 150, "promedio_ms": float("inf"), "alcanzable": "yes"},
            {"host": "valid", "perdida_pct": 2.5, "promedio_ms": 4, "alcanzable": False},
        ]}}

        event = topology_event(topology)
        metrics = event["payload"]["path_metrics"]
        self.assertEqual(metrics[0]["perdida_pct"], None)
        self.assertEqual(metrics[0]["promedio_ms"], None)
        self.assertIsNone(metrics[0]["alcanzable"])
        self.assertEqual(metrics[1]["perdida_pct"], 2.5)
        self.assertEqual(metrics[1]["promedio_ms"], 4)
        self.assertIs(metrics[1]["alcanzable"], False)

    def test_topology_event_ignores_malformed_optional_metrics(self):
        event = topology_event({"ts": "2026-08-06T00:00:00Z", "monitorizacion": {"saltos": [None, "invalid"]}})
        self.assertEqual(event["payload"]["path_metrics"], [])

        event = topology_event({"monitorizacion": {"saltos": "invalid"}})
        self.assertEqual(event["payload"]["path_metrics"], [])

    def test_client_is_opt_in_and_sends_to_test_adapter(self):
        skipped = TelemetryClient(url="http://127.0.0.1:3049/events", enabled=False).send_event({"x": 1})
        self.assertTrue(skipped["skipped"])
        response = Mock(status=202)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        opener = Mock()
        opener.open.return_value = response
        with patch("core.telemetry.urllib.request.build_opener", return_value=opener) as build_opener:
            result = TelemetryClient(url="http://127.0.0.1:3049/events", token="test-token", enabled=True).send_event({"x": 1})
        self.assertTrue(any(isinstance(handler, _NoRedirectHandler) for handler in build_opener.call_args.args))
        self.assertTrue(result["sent"])
        request = opener.open.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"x": 1})
        self.assertEqual(request.headers["Authorization"], "Bearer test-token")

    def test_non_json_events_are_rejected_without_network_request(self):
        opener = Mock()
        with patch("core.telemetry.urllib.request.build_opener", return_value=opener):
            result = TelemetryClient(
                url="http://127.0.0.1:3049/events", enabled=True
            ).send_event({"value": object()})

        self.assertFalse(result["sent"])
        self.assertEqual(result["error"], "evento no serializable")
        opener.open.assert_not_called()

    def test_non_finite_numbers_are_rejected_without_network_request(self):
        opener = Mock()
        with patch("core.telemetry.urllib.request.build_opener", return_value=opener):
            result = TelemetryClient(
                url="http://127.0.0.1:3049/events", enabled=True
            ).send_event({"latency": float("nan")})

        self.assertFalse(result["sent"])
        self.assertEqual(result["error"], "evento no serializable")
        opener.open.assert_not_called()

    def test_redirects_are_not_followed(self):
        handler = _NoRedirectHandler()
        redirected = handler.redirect_request(
            Mock(), Mock(), 302, "Found", {}, "https://other.example/events"
        )
        self.assertIsNone(redirected)

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
