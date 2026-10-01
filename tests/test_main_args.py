import contextlib
import io
import sys
import unittest
from types import SimpleNamespace
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

    def test_network_target_options_reject_option_like_values(self):
        for option in ("--hunt", "--traceroute", "--topology", "--infra-check", "--topology-watch"):
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    self._parse(f"{option}=-I")
            self.assertEqual(raised.exception.code, 2)

    def test_network_targets_are_trimmed_consistently(self):
        args = self._parse(
            "--hunt", " 192.0.2.1 ",
            "--traceroute", " 192.0.2.2 ",
            "--topology", " 192.0.2.3 ",
            "--infra-check", " 192.0.2.4 ",
            "--topology-watch", " 192.0.2.5 ",
        )
        self.assertEqual(
            [args.hunt, args.traceroute, args.topology, args.infra_check, args.topology_watch],
            [f"192.0.2.{n}" for n in range(1, 6)],
        )

    def test_infra_check_accepts_optional_target(self):
        default = self._parse("--infra-check")
        explicit = self._parse("--infra-check", "192.0.2.1")
        self.assertEqual(default.infra_check, "8.8.8.8")
        self.assertEqual(explicit.infra_check, "192.0.2.1")

    def test_watch_uses_validated_cli_interval(self):
        with patch.object(main, "parse_args", return_value=SimpleNamespace(
            version=False, setup=False, watch=True, watch_interval=15,
            scan=False, web=False, internet=False, report=False,
            connect=False, lan=False, hunt=None, health=False,
            traceroute=None, topology_watch=None, infra_check=None,
            topology=None, noc=False,
        )), patch("core.monitor.monitoreo_continuo") as monitor:
            with self.assertRaises(SystemExit) as raised:
                main.main()
        self.assertEqual(raised.exception.code, 0)
        monitor.assert_called_once_with(intervalo=15)

    def test_watch_interval_rejects_values_below_minimum(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self._parse("--watch-interval", "9")
        self.assertEqual(raised.exception.code, 2)

    def test_watch_interval_accepts_daily_limit_and_rejects_larger_values(self):
        args = self._parse("--watch-interval", "86400")
        self.assertEqual(args.watch_interval, 86400)

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self._parse("--watch-interval", "86401")
        self.assertEqual(raised.exception.code, 2)

    def test_watch_cycles_rejects_negative_values(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self._parse("--watch-cycles", "-1")
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
