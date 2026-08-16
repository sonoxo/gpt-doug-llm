"""
✓ 6/10 API Gateway — REST API wrapping Zyra + Sentinel + Golden Shield
Deploy: python3 -m api_gateway.server (free, stdlib only)
       or AWS Lambda + API Gateway (free tier)

Endpoints:
  GET  /health          — system status
  POST /inspect          — Zyra inspect text
  POST /sentinel/scan    — run vulnerability scan
  POST /shield/check     — Golden Shield inbound check
  POST /shield/sterilize — Golden Shield output sterilize
  GET  /knowledge/search?query=... — search knowledge base
  POST /review/pr         — review a pull request
  POST /payment/create    — create crypto payment
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

_PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT))

PORT = int(os.environ.get("API_PORT", "9090"))

class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, code, data):
        body = json.dumps(data, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0: return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "online", "agent": "gpt-doug", "version": "1.0",
                                   "zyra": "ZYRA/3.0", "shield": "GOLDEN-SHIELD/1.0",
                                   "sentinel": "ZYRA-SENTINEL/1.0", "knowledge_entries": 173})
        elif path == "/knowledge/search":
            qs = parse_qs(urlparse(self.path).query)
            query = qs.get("query", [""])[0]
            from ontology import Ontology
            links = Ontology.task_knowledge("search", query, top_n=5)
            entries = {e["id"]: e for e in Ontology.knowledge()}
            results = [{"id": entries.get(l["to"][1],{}).get("id"),
                       "summary": entries.get(l["to"][1],{}).get("summary","")[:100],
                       "confidence": l.get("confidence")} for l in links if entries.get(l["to"][1])]
            self._send_json(200, {"query": query, "results": results})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return

        if path == "/inspect":
            from zyra import Zyra
            zyra = Zyra()
            verdict = zyra.inspect(body.get("text",""), body.get("direction","input"))
            self._send_json(200, {"allowed": verdict.allowed, "risk": verdict.risk,
                                 "reasons": verdict.reasons, "classification": verdict.classification,
                                 "rice_signals": verdict.rice_signals, "redacted": verdict.text != body.get("text","")})

        elif path == "/sentinel/scan":
            from golden_shield import ZyraSentinel
            sentinel = ZyraSentinel()
            scan_type = body.get("type", "internal")
            if scan_type == "full":
                report = sentinel.full_sweep()
                self._send_json(200, {"scan_id": report.scan_id, "total": report.total_findings,
                                     "critical": report.critical_count, "duration": report.duration_seconds})
            else:
                findings = {"internal": sentinel.scan_internal, "external": sentinel.scan_external,
                           "satellite": sentinel.scan_satellite, "darkweb": sentinel.scan_darkweb_exposure}.get(scan_type, sentinel.scan_internal)()
                self._send_json(200, {"type": scan_type, "count": len(findings),
                                     "findings": [{"severity": f.severity, "target": f.target, "description": f.description[:80]} for f in findings[:10]]})

        elif path == "/shield/check":
            from golden_shield import GoldenShield
            shield = GoldenShield()
            a = shield.inspect_inbound(body.get("text",""), body.get("source","api"))
            self._send_json(200, {"action": a.action, "risk": a.risk_level, "reason": a.reason,
                                 "rate_limited": a.rate_limited, "classification": a.classification})

        elif path == "/shield/sterilize":
            from golden_shield import GoldenShield
            shield = GoldenShield()
            a = shield.inspect_outbound(body.get("text",""), "model")
            safe = a.zyra_verdict.text if a.zyra_verdict else body.get("text","")
            self._send_json(200, {"action": a.action, "safe_text": safe, "signals": a.threat_signals})

        elif path == "/review/pr":
            from hackathon.agents.code_reviewer import review_pr
            result = review_pr(body)
            self._send_json(200, result)

        elif path == "/payment/create":
            from crypto.payment_sdk import CryptoPayment
            cp = CryptoPayment()
            payment = cp.create_payment(body.get("amount", 19.0), body.get("currency","usd"), body.get("crypto","btc"))
            self._send_json(200, {"payment_id": payment.payment_id, "address": payment.address,
                                 "amount": payment.amount, "crypto": payment.crypto, "status": payment.status})
        else:
            self._send_json(404, {"error": "not found"})

    def log_message(self, *a): pass  # silent

def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), APIHandler)
    print(f"🛰️ GPT Doug API Gateway running on port {PORT}")
    print(f"   Health:  http://localhost:{PORT}/health")
    print(f"   Inspect: http://localhost:{PORT}/inspect")
    print(f"   Scan:    http://localhost:{PORT}/sentinel/scan")
    print(f"   Shield: http://localhost:{PORT}/shield/check")
    server.serve_forever()

if __name__ == "__main__":
    main()
