import contextlib
import io
import sys
import unittest
from unittest.mock import patch

import main


class MainArgumentTests(unittest.TestCase):
    def _parse(self, *arguments):
        with patch.object(sys, "argv", ["visor", *arguments]):
            return main.parse_args()

    def test_watch_arguments_accept_safe_values(self):
        args = self._parse("--topology-watch", "1.1.1.1", "--watch-interval", "10", "--watch-cycles", "2")
        self.assertEqual(args.watch_interval, 10)
        self.assertEqual(args.watch_cycles, 2)

    def test_watch_interval_rejects_values_below_minimum(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self._parse("--watch-interval", "9")
        self.assertEqual(raised.exception.code, 2)

    def test_watch_cycles_rejects_negative_values(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self._parse("--watch-cycles", "-1")
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
