import unittest
from unittest.mock import patch

from ui.setup_wizard import _paso_smtp


class SetupWizardTests(unittest.TestCase):
    @patch("ui.setup_wizard.getpass", return_value="app-password")
    @patch("builtins.input", side_effect=["s", "sender@example.com", "recipient@example.com"])
    def test_smtp_password_is_read_without_terminal_echo(self, _input, _getpass):
        result = _paso_smtp()

        self.assertEqual(result["clave"], "app-password")
        _getpass.assert_called_once()
        self.assertNotIn("app-password", [call.args[0] for call in _input.call_args_list])


if __name__ == "__main__":
    unittest.main()
