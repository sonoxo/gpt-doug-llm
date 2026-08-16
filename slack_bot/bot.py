"""
✓ 10/10 Slack/Discord Bot — Zyra Sentinel as a team security bot
Free: Slack free tier (10K messages), ngrok for webhook (free)
Deploy: python3 slack_bot/bot.py

Commands:
  /sentinel scan     — run internal scan on the host machine
  /sentinel status   — show sentinel status
  /shield check <text> — run Golden Shield check on text
  /knowledge <query>  — search the knowledge base
  /review <diff>      — review a code diff for security issues
"""
from __future__ import annotations

import json
import os
import sys
import hmac
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT))

PORT = int(os.environ.get("BOT_PORT", "3000"))
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

def handle_command(text: str) -> dict:
    """Handle a Slack slash command or message."""
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "scan":
        from golden_shield import ZyraSentinel
        sentinel = ZyraSentinel()
        findings = sentinel.scan_internal()
        if not findings:
            return {"text": "✅ System secure. No threats detected."}
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": f"🚨 *{len(findings)} findings*"}}]
        for f in findings[:10]:
            blocks.append({"type": "section", "text": {"type": "mrkdwn",
                         "text": f"*[{f.severity}]* {f.category}: {f.description[:80]}"}})
        return {"blocks": blocks}

    elif cmd == "status":
        from golden_shield import ZyraSentinel
        sentinel = ZyraSentinel()
        return {"text": sentinel.display()}

    elif cmd == "shield":
        if not arg:
            return {"text": "Usage: /sentinel shield <text to check>"}
        from golden_shield import GoldenShield
        shield = GoldenShield()
        a = shield.inspect_inbound(arg, "slack")
        emoji = {"ALLOW": "✅", "QUARANTINE": "⚠️", "BLOCK": "🚫", "ELIMINATE": "💀"}.get(a.action, "❓")
        return {"text": f"{emoji} *{a.action}* — {a.reason}"}

    elif cmd == "knowledge":
        if not arg:
            return {"text": "Usage: /sentinel knowledge <search query>"}
        from ontology import Ontology
        links = Ontology.task_knowledge("search", arg, top_n=3)
        entries = {e["id"]: e for e in Ontology.knowledge()}
        if not links:
            return {"text": "No matching knowledge entries."}
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": f"📚 *Knowledge search: {arg}*"}}]
        for link in links:
            entry = entries.get(link["to"][1])
            if entry:
                blocks.append({"type": "section", "text": {"type": "mrkdwn",
                             "text": f"• *{entry.get('id')}* ({entry.get('attribution','?')})\n  {entry.get('summary','')[:100]}\n  Confidence: {link.get('confidence')}"}})
        return {"blocks": blocks}

    elif cmd == "review":
        if not arg:
            return {"text": "Usage: /sentinel review <code diff>"}
        from hackathon.agents.code_reviewer import review_pr
        result = review_pr({"number":0,"title":"Slack review","body":"","diff":arg,"files":[],"author":"slack"})
        return {"text": result["comment"]}

    elif cmd == "help":
        return {"text": "*Commands:*\n• `/sentinel scan` — run security scan\n• `/sentinel status` — sentinel status\n• `/sentinel shield <text>` — Golden Shield check\n• `/sentinel knowledge <query>` — search knowledge base\n• `/sentinel review <diff>` — review code"}

    else:
        return {"text": f"Unknown command: {cmd}. Try `/sentinel help`"}


class SlackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))

        # Verify Slack signature (if secret set)
        if SLACK_SIGNING_SECRET:
            timestamp = self.headers.get("X-Slack-Request-Timestamp", "")
            sig_basestring = f"v0:{timestamp}:{body.decode()}".encode()
            my_sig = "v0=" + hmac.new(SLACK_SIGNING_SECRET.encode(), sig_basestring, __import__("hashlib").sha256).hexdigest()
            slack_sig = self.headers.get("X-Slack-Signature", "")
            if not hmac.compare_digest(my_sig, slack_sig):
                self.send_response(401); self.end_headers(); return

        from urllib.parse import parse_qs
        params = parse_qs(body.decode())
        text = params.get("text", ["help"])[0]
        response = handle_command(text)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, *a): pass


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), SlackHandler)
    print(f"🛰️ GPT Doug Slack Bot running on port {PORT}")
    print(f"   Commands: scan, status, shield, knowledge, review, help")
    print(f"   Set SLACK_SIGNING_SECRET for production")
    server.serve_forever()

if __name__ == "__main__":
    main()
