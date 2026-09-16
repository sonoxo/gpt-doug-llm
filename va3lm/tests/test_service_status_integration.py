from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import unittest
from unittest.mock import patch

from va3lm.service_status import service_status


class ServiceStatusIntegrationTests(unittest.TestCase):
    def test_real_local_http_status_contracts(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append(self.path)
                payload = {"ok": True, "chainId": "xunia-main-v1", "height": 0} if self.path == '/health' else {"mode": "VA3LM", "foundryConfigured": False, "detector": {"reachable": False}}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

        with HTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f'http://127.0.0.1:{server.server_port}'
                with patch.dict('os.environ', {'XUNIA_CHAIN_BASE_URL':base, 'ZYRA_LIVE_BASE_URL':base}):
                    chain = service_status('XUNIA_CHAIN')
                    geo = service_status('GEOVISION')
                self.assertEqual(chain['executionState'], 'STATUS_OBSERVED')
                self.assertFalse(geo['serviceReported']['foundryConfigured'])
                self.assertFalse(geo['serviceReported']['detectorReachable'])
                self.assertEqual(requests, ['/health','/api/va3lm/geovision/status'])
            finally:
                server.shutdown()
                thread.join()

    def test_missing_and_invalid_configuration_never_dispatch(self):
        for base, expected in [('', 'SERVICE_UNCONFIGURED'), ('file:///tmp/data','SERVICE_CONFIGURATION_INVALID'), ('http://user:secret@localhost','SERVICE_CONFIGURATION_INVALID'), ('http://localhost/arbitrary','SERVICE_CONFIGURATION_INVALID')]:
            with patch.dict('os.environ', {'XUNIA_CHAIN_BASE_URL':base}):
                self.assertEqual(service_status('XUNIA_CHAIN')['executionState'], expected)


if __name__ == '__main__':
    unittest.main()
