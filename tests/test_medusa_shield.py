import tempfile
import unittest
from pathlib import Path

from core.medusa_shield import scan_for_secrets


class MedusaShieldTests(unittest.TestCase):
    def test_reports_secret_type_and_line_without_exposing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.txt"
            path.write_text("safe\napi_key = 'abcdefghijklmnop'\n", encoding="utf-8")

            findings = scan_for_secrets(directory)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "GENERIC_API_KEY")
        self.assertEqual(findings[0]["line"], 2)
        self.assertNotIn("abcdefghijklmnop", findings[0])

    def test_skips_unreadable_text_without_aborting_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "broken.txt"
            invalid.write_bytes(b"\xff\xfe")
            readable = Path(directory) / "readable.txt"
            readable.write_text("PRIVATE_KEY: -----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")

            findings = scan_for_secrets(directory)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["file"], str(readable))


if __name__ == "__main__":
    unittest.main()
