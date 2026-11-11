import contextlib
import io
import sys
import unittest
from unittest.mock import patch

import main
from ui.menu import abrir_test_ipv6


class IPv6BrowserLinkTests(unittest.TestCase):
    def test_cli_recognizes_ipv6_flag(self):
        with patch.object(sys, 'argv', ['visor', '--ipv6']):
            self.assertTrue(main.parse_args().ipv6)

    def test_opens_only_requested_site_without_claiming_result(self):
        output = io.StringIO()
        with patch('webbrowser.open', return_value=True) as browser, contextlib.redirect_stdout(output):
            self.assertTrue(abrir_test_ipv6())
        browser.assert_called_once_with('https://test-ipv6.com/', new=2)
        self.assertIn('no obtiene ni guarda', output.getvalue())
        self.assertIn('IP pública', output.getvalue())

    def test_browser_failure_shows_manual_url(self):
        output = io.StringIO()
        with patch('webbrowser.open', return_value=False), contextlib.redirect_stdout(output):
            self.assertFalse(abrir_test_ipv6())
        self.assertIn('https://test-ipv6.com/', output.getvalue())
        self.assertIn('No se pudo abrir', output.getvalue())

    def test_browser_error_is_handled(self):
        with patch('webbrowser.open', side_effect=OSError('cannot open')), contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(abrir_test_ipv6())

    def test_cli_dispatch_and_failure_exit(self):
        with patch.object(sys, 'argv', ['visor', '--ipv6']), patch('ui.menu.abrir_test_ipv6', return_value=False) as opener:
            with self.assertRaises(SystemExit) as result:
                main.main()
        self.assertEqual(result.exception.code, 1)
        opener.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
