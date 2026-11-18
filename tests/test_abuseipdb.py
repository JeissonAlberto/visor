import contextlib
import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
from core.abuseipdb import consultar_ip, _NoRedirect, MAX_RESPONSE


class AbuseTests(unittest.TestCase):
    def response(self, data):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'data': data}).encode()
        return response

    def test_success_and_request_parameters(self):
        opener = MagicMock()
        opener.open.return_value = self.response({'ipAddress':'8.8.8.8', 'abuseConfidenceScore':10, 'totalReports':2, 'isp':'Example\x1b[31m', 'countryCode':'US'})
        with patch('core.abuseipdb.urllib.request.build_opener', return_value=opener):
            result = consultar_ip('8.8.8.8', 'secret-key')
        self.assertTrue(result['ok'])
        request = opener.open.call_args.args[0]
        self.assertNotIn('secret-key', request.full_url)
        self.assertEqual(request.get_header('Key'), 'secret-key')
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 10)
        self.assertNotIn('\x1b', result['isp'])
        self.assertEqual(result['score'], 10)

    def test_private_invalid_or_missing_key_never_calls_network(self):
        for address, key in [('192.168.1.1','key'), ('224.0.0.1','key'), ('abc','key'), ('8.8.8.8','')]:
            with self.subTest(address=address), patch('core.abuseipdb.urllib.request.build_opener') as op:
                self.assertFalse(consultar_ip(address, key)['ok'])
                op.assert_not_called()

    def test_ipv6_and_url_encoding(self):
        opener = MagicMock()
        opener.open.return_value = self.response({'ipAddress':'2606:4700:4700::1111','abuseConfidenceScore':0,'totalReports':0})
        with patch('core.abuseipdb.urllib.request.build_opener', return_value=opener):
            self.assertTrue(consultar_ip('2606:4700:4700::1111','key')['ok'])
        self.assertIn('%3A', opener.open.call_args.args[0].full_url)

    def test_http_errors_do_not_expose_body_or_key(self):
        for code in (401, 403, 429, 500):
            opener = MagicMock(); opener.open.side_effect = urllib.error.HTTPError('https://example', code, 'secret-key', {}, None)
            with patch('core.abuseipdb.urllib.request.build_opener', return_value=opener):
                result = consultar_ip('8.8.8.8','secret-key')
            self.assertFalse(result['ok']); self.assertNotIn('secret-key', str(result))
            if code == 429: self.assertIn('Límite', result['error'])

    def test_invalid_response_and_size_limit(self):
        for payload in [b'not json', b'X'*(MAX_RESPONSE+1), b'{"data":{"ipAddress":"1.1.1.1","abuseConfidenceScore":1,"totalReports":0}}']:
            opener = MagicMock(); opener.open.return_value.__enter__.return_value.read.return_value = payload
            with patch('core.abuseipdb.urllib.request.build_opener', return_value=opener):
                self.assertFalse(consultar_ip('8.8.8.8','key')['ok'])

    def test_redirects_are_refused(self):
        self.assertIsNone(_NoRedirect().redirect_request(None,None,302,'redirect',{},'https://elsewhere.test/'))

    def test_ui_output_and_cli_parse(self):
        import main
        from ui.menu import consultar_abuseip
        with patch('core.abuseipdb.consultar_ip', return_value={'ok':True,'ip':'8.8.8.8','score':0,'reports':0,'days':90,'last_reported':None,'country':None,'isp':None}), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertTrue(consultar_abuseip('8.8.8.8'))
        self.assertIn('no prueba concluyente', out.getvalue())
        with patch('sys.argv',['visor','--abuseip','8.8.8.8']):
            self.assertEqual(main.parse_args().abuseip, '8.8.8.8')


if __name__ == '__main__':
    unittest.main()
