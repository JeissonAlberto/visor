import os
import ssl
import unittest
from unittest.mock import patch

from core import proxmox_agent
from core.proxmox_agent import PROXMOX_MAX_RESPONSE_BYTES


class ProxmoxAgentTests(unittest.TestCase):
    def test_unexpected_json_shapes_are_rejected(self):
        bodies = (b"[]", b'{"data": {}}', b'{"data": [null]}', b'{"errors": {"message": "denied"}}')
        for body in bodies:
            with self.subTest(body=body):
                response = unittest.mock.MagicMock()
                response.__enter__.return_value.read.return_value = body
                with patch.object(
                    proxmox_agent, "_proxmox_ssl_context", return_value=ssl.create_default_context()
                ), patch("core.proxmox_agent.urllib.request.urlopen", return_value=response):
                    result = proxmox_agent._proxmox_get(
                        "proxmox.example", "root@pam!visor", "secret-token", "/nodes"
                    )

                self.assertEqual(result, proxmox_agent.PROXMOX_INVALID_RESPONSE)

    def test_large_response_is_rejected_with_stable_error(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"{" * (PROXMOX_MAX_RESPONSE_BYTES + 1)
        with patch.object(proxmox_agent, "_proxmox_ssl_context", return_value=ssl.create_default_context()), patch(
            "core.proxmox_agent.urllib.request.urlopen", return_value=response
        ) as urlopen:
            result = proxmox_agent._proxmox_get(
                "proxmox.example", "root@pam!visor", "secret-token", "/nodes"
            )

        self.assertEqual(result, {"error": "La respuesta de la API de Proxmox supera el límite permitido."})
        response.__enter__.return_value.read.assert_called_once_with(PROXMOX_MAX_RESPONSE_BYTES + 1)
        self.assertNotIn("secret-token", str(result))
        urlopen.assert_called_once()

    def test_response_within_limit_is_parsed(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"data": []}'
        with patch.object(proxmox_agent, "_proxmox_ssl_context", return_value=ssl.create_default_context()), patch(
            "core.proxmox_agent.urllib.request.urlopen", return_value=response
        ):
            result = proxmox_agent._proxmox_get(
                "proxmox.example", "root@pam!visor", "secret-token", "/nodes"
            )

        self.assertEqual(result, {"data": []})

    def test_tls_context_verifies_system_ca_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VISOR_PROXMOX_CA_FILE", None)
            os.environ.pop("VISOR_PROXMOX_INSECURE_TLS", None)
            context = proxmox_agent._proxmox_ssl_context("proxmox.example")

        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_ip_context_keeps_chain_verification_without_hostname_match(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VISOR_PROXMOX_CA_FILE", None)
            os.environ.pop("VISOR_PROXMOX_INSECURE_TLS", None)
            context = proxmox_agent._proxmox_ssl_context("192.0.2.10")

        self.assertFalse(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_insecure_tls_requires_explicit_environment_flag(self):
        with patch.dict(os.environ, {"VISOR_PROXMOX_INSECURE_TLS": "1"}, clear=False):
            os.environ.pop("VISOR_PROXMOX_CA_FILE", None)
            context = proxmox_agent._proxmox_ssl_context("proxmox.example")

        self.assertFalse(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)

    def test_invalid_ca_path_returns_stable_redacted_error(self):
        with patch.dict(
            os.environ,
            {"VISOR_PROXMOX_CA_FILE": "/path/that/does/not/exist.pem"},
            clear=False,
        ):
            result = proxmox_agent._proxmox_get(
                "proxmox.example", "root@pam!visor", "secret-token", "/nodes"
            )

        self.assertEqual(result, {"error": "No fue posible consultar la API de Proxmox."})
        self.assertNotIn("secret-token", str(result))
        self.assertNotIn("proxmox.example", str(result))

    def test_http_protocol_errors_return_stable_redacted_error(self):
        import http.client

        with patch.object(
            proxmox_agent, "_proxmox_ssl_context", return_value=ssl.create_default_context()
        ), patch(
            "core.proxmox_agent.urllib.request.urlopen",
            side_effect=http.client.BadStatusLine("secret-host internal response"),
        ):
            result = proxmox_agent._proxmox_get(
                "proxmox.example", "root@pam!visor", "secret-token", "/nodes"
            )

        self.assertEqual(result, {"error": "No fue posible consultar la API de Proxmox."})
        self.assertNotIn("secret-host", str(result))
        self.assertNotIn("secret-token", str(result))

    def test_node_metrics_reject_invalid_numeric_values_without_crashing(self):
        invalid_nodes = (
            {"cpu": "unknown"},
            {"mem": None},
            {"uptime": float("nan")},
            {"cpu": 1.1},
            {"disk": -1},
            {"mem": 10**1000},
        )
        for invalid in invalid_nodes:
            with self.subTest(invalid=invalid):
                node = {"cpu": 0.25, "maxmem": 8, "mem": 4, "maxdisk": 16,
                        "disk": 8, "uptime": 3600, **invalid}
                with patch.object(proxmox_agent, "ping_proxmox", return_value=True), patch.object(
                    proxmox_agent, "_proxmox_get", return_value={"data": [node]}
                ):
                    self.assertEqual(
                        proxmox_agent.get_nodes_status("proxmox.example"),
                        [proxmox_agent.PROXMOX_INVALID_RESPONSE],
                    )

    def test_vm_metrics_reject_invalid_numeric_values_without_crashing(self):
        for invalid in ({"mem": "large"}, {"uptime": True}, {"cpu": float("inf")}):
            with self.subTest(invalid=invalid), patch.object(
                proxmox_agent, "_proxmox_get", return_value={"data": [{
                    "cpu": 0.5, "mem": 1024, "uptime": 7200, **invalid
                }]}
            ):
                self.assertEqual(
                    proxmox_agent.get_vms_status("proxmox.example", "node1"),
                    [proxmox_agent.PROXMOX_INVALID_RESPONSE],
                )

    def test_valid_node_and_vm_metrics_keep_existing_output_units(self):
        node = {"node": "node1", "status": "online", "cpu": 0.5,
                "maxmem": 2 * 1024**3, "mem": 1024**3,
                "maxdisk": 4 * 1024**3, "disk": 2 * 1024**3, "uptime": 7200}
        vm = {"vmid": 100, "name": "vm1", "status": "running",
              "cpu": 0.25, "mem": 512 * 1024**2, "uptime": 3600}
        with patch.object(proxmox_agent, "ping_proxmox", return_value=True), patch.object(
            proxmox_agent, "_proxmox_get", return_value={"data": [node]}
        ):
            node_result = proxmox_agent.get_nodes_status("proxmox.example")
        with patch.object(proxmox_agent, "_proxmox_get", return_value={"data": [vm]}):
            vm_result = proxmox_agent.get_vms_status("proxmox.example", "node1")

        self.assertEqual(node_result[0]["cpu_pct"], 50.0)
        self.assertEqual(node_result[0]["mem_pct"], 50.0)
        self.assertEqual(node_result[0]["uptime_h"], 2.0)
        self.assertEqual(vm_result[0]["cpu_pct"], 25.0)
        self.assertEqual(vm_result[0]["mem_mb"], 512.0)
        self.assertEqual(vm_result[0]["uptime_h"], 1.0)

    def test_node_query_preserves_redacted_api_failure(self):
        with (
            patch.object(proxmox_agent, "ping_proxmox", return_value=True),
            patch.object(
                proxmox_agent,
                "_proxmox_get",
                return_value={"error": "No fue posible consultar la API de Proxmox."},
            ),
        ):
            result = proxmox_agent.get_nodes_status("proxmox.example")

        self.assertEqual(
            result,
            [{"error": "No fue posible consultar la API de Proxmox."}],
        )

    def test_vm_query_preserves_redacted_api_failure(self):
        with patch.object(
            proxmox_agent,
            "_proxmox_get",
            return_value={"error": "No fue posible consultar la API de Proxmox."},
        ):
            result = proxmox_agent.get_vms_status("proxmox.example", "node1")

        self.assertEqual(
            result,
            [{"error": "No fue posible consultar la API de Proxmox."}],
        )

    def test_ping_closes_socket_when_connect_fails(self):
        with patch("core.proxmox_agent.socket.socket") as socket_factory:
            sock = socket_factory.return_value
            sock.connect_ex.side_effect = OSError("unreachable")

            self.assertFalse(proxmox_agent.ping_proxmox("192.0.2.10"))

        sock.close.assert_called_once_with()
        sock.settimeout.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
