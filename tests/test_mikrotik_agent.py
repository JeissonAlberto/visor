import subprocess
import unittest
from unittest.mock import patch

from core.mikrotik_agent import _ssh_cmd, ping_mikrotik


class MikrotikAgentTests(unittest.TestCase):
    @patch("core.mikrotik_agent.subprocess.run")
    def test_ssh_accepts_new_host_keys_but_checks_known_changes(self, run):
        run.return_value.stdout = "router\n"

        result = _ssh_cmd("192.0.2.10", "admin", "unused", ":put identity", timeout=7)

        self.assertEqual(result, "router")
        command = run.call_args.args[0]
        self.assertIn("StrictHostKeyChecking=accept-new", command)
        self.assertNotIn("StrictHostKeyChecking=no", command)
        self.assertEqual(run.call_args.kwargs["timeout"], 9)

    @patch("core.mikrotik_agent.subprocess.run", side_effect=subprocess.TimeoutExpired("ssh", 7))
    def test_ssh_timeout_is_reported_without_escaping(self, _run):
        result = _ssh_cmd("192.0.2.10", "admin", "unused", ":put identity", timeout=7)

        self.assertTrue(result.startswith("ERROR:"))

    @patch("core.mikrotik_agent.socket.socket")
    def test_ping_closes_socket_when_connection_fails(self, socket_factory):
        context = socket_factory.return_value
        socket = context.__enter__.return_value
        socket.connect_ex.side_effect = OSError("unavailable")

        self.assertFalse(ping_mikrotik("192.0.2.10"))
        context.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
