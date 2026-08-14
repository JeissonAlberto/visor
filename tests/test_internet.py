import ssl
import unittest

from core.test_internet import _ssl_ctx


class InternetSecurityTests(unittest.TestCase):
    def test_speed_test_context_verifies_certificates_and_hostnames(self):
        context = _ssl_ctx()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)


if __name__ == "__main__":
    unittest.main()
