import contextlib
import io
import unittest
from unittest.mock import patch

from ui import menu_infraestructura


class ProxmoxMenuTests(unittest.TestCase):
    def test_api_query_error_is_not_mislabeled_as_authentication_failure(self):
        output = io.StringIO()
        with (
            patch("core.proxmox_agent.ping_proxmox", return_value=True),
            patch("core.proxmox_agent.get_nodes_status", return_value=[
                {"error": "No fue posible consultar la API de Proxmox."}
            ]),
            patch("ui.menu_infraestructura.getpass", return_value="secret"),
            patch("builtins.input", return_value=""),
            contextlib.redirect_stdout(output),
        ):
            menu_infraestructura._menu_proxmox()

        text = output.getvalue()
        self.assertIn("No fue posible consultar la API", text)
        self.assertNotIn("Error de autenticación", text)
        self.assertIn("CA/TLS", text)


if __name__ == "__main__":
    unittest.main()
