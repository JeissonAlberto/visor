import smtplib
import unittest
from unittest.mock import MagicMock, patch

from core.mail import enviar_correo


class MailTests(unittest.TestCase):
    def setUp(self):
        self.config = patch.multiple(
            "core.mail",
            ALERTAS_EMAIL_ACTIVAS=True,
            SMTP_SERVER="smtp.example.test",
            SMTP_PORT=465,
            SMTP_USER="sender@example.test",
            SMTP_PASS="configured-test-value",
            DESTINATARIO="recipient@example.test",
        )
        self.config.start()
        self.addCleanup(self.config.stop)

    def test_expected_smtp_failure_returns_false(self):
        with patch(
            "core.mail.smtplib.SMTP_SSL",
            side_effect=smtplib.SMTPException("authentication failed"),
        ):
            self.assertFalse(enviar_correo("subject", "body"))

    def test_unexpected_programming_error_is_not_hidden(self):
        with patch(
            "core.mail.smtplib.SMTP_SSL",
            side_effect=RuntimeError("unexpected"),
        ):
            with self.assertRaises(RuntimeError):
                enviar_correo("subject", "body")

    def test_success_sends_message(self):
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        with patch("core.mail.smtplib.SMTP_SSL", return_value=smtp) as smtp_ssl:
            self.assertTrue(enviar_correo("subject", "body"))

        smtp_ssl.assert_called_once()
        smtp.login.assert_called_once_with("sender@example.test", "configured-test-value")
        smtp.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
