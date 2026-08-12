import os
import ssl
import unittest
from unittest.mock import patch

from core import proxmox_agent


class ProxmoxAgentTests(unittest.TestCase):
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

    def test_invalid_ca_path_is_reported_without_raising(self):
        with patch.dict(
            os.environ,
            {"VISOR_PROXMOX_CA_FILE": "/path/that/does/not/exist.pem"},
            clear=False,
        ):
            result = proxmox_agent._proxmox_get(
                "proxmox.example", "root@pam!visor", "placeholder", "/nodes"
            )

        self.assertIn("error", result)
        self.assertNotIn("placeholder", result["error"])

    def test_ping_closes_socket_when_connect_fails(self):
        with patch("core.proxmox_agent.socket.socket") as socket_factory:
            sock = socket_factory.return_value
            sock.connect_ex.side_effect = OSError("unreachable")

            self.assertFalse(proxmox_agent.ping_proxmox("192.0.2.10"))

        sock.close.assert_called_once_with()
        sock.settimeout.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
