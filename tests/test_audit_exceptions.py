import tempfile
import unittest
from pathlib import Path

from scripts.audit_exceptions import scan


class AuditExceptionsTests(unittest.TestCase):
    def test_finds_bare_and_broad_handlers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.py").write_text(
                "try:\n    work()\nexcept:\n    pass\n\ntry:\n    work()\nexcept Exception:\n    pass\n",
                encoding="utf-8",
            )
            findings = scan(root, set())
            self.assertEqual(len(findings), 2)
            self.assertEqual(findings[0].kind, "bare_except")
            self.assertEqual(findings[1].exception, "Exception")

    def test_ignores_specific_handlers_and_excluded_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "good.py").write_text(
                "try:\n    work()\nexcept (OSError, ValueError):\n    pass\n",
                encoding="utf-8",
            )
            excluded = root / ".venv"
            excluded.mkdir()
            (excluded / "bad.py").write_text("try:\n    work()\nexcept:\n    pass\n", encoding="utf-8")
            findings = scan(root, {".venv"})
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
