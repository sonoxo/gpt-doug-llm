#!/usr/bin/env python3
"""Post a real comment to YouTube as your own account, via the official
YouTube Data API v3 with OAuth 2.0 — not a bot/spam script. Only ever
posts on your explicit command, only to your account.

Setup (one-time, you must do this yourself — I can't create Google
credentials on your behalf):
  1. https://console.cloud.google.com/ -> create a project.
  2. Enable "YouTube Data API v3" for that project.
  3. Create OAuth client credentials, type "Desktop app".
  4. Set the two env vars below to the client_id / client_secret shown.

Usage:
  export YOUTUBE_CLIENT_ID=...
  export YOUTUBE_CLIENT_SECRET=...
  python3 youtube_comment.py authorize        # one-time browser consent
  python3 youtube_comment.py post <video_id> "comment text"
"""
from __future__ import annotations

import json
import os
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
REDIRECT_PORT = 8912
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

TOKEN_DIR = os.path.join(os.path.expanduser("~"), ".gpt-doug")
TOKEN_PATH = os.path.join(TOKEN_DIR, "youtube_token.json")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
COMMENT_URL = "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet"


def _require_client_creds():
    if not CLIENT_ID or not CLIENT_SECRET:
        sys.exit(
            "YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET not set.\n"
            "Create OAuth credentials at https://console.cloud.google.com/ "
            "(APIs & Services -> Credentials -> Create OAuth client, type "
            "'Desktop app'), then export both env vars and re-run."
        )


class _CallbackHandler(BaseHTTPRequestHandler):
    code = None

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CallbackHandler.code = params.get("code", [None])[0]
        body = b"<html><body>Authorized. You can close this tab and return to the terminal.</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def authorize():
    """Interactive one-time OAuth consent flow. Opens your real browser,
    you log into YOUR Google account and approve, we never see your
    password — only Google's own consent screen handles that."""
    _require_client_creds()
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    print(f"Opening browser for Google consent:\n{url}\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout=180)
    server.server_close()

    if not _CallbackHandler.code:
        sys.exit("No authorization code received (timed out or denied).")

    body = urllib.parse.urlencode({
        "code": _CallbackHandler.code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, body, method="POST")
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read())

    if "refresh_token" not in tokens:
        sys.exit(f"No refresh_token in response (already authorized before? revoke access and retry): {tokens}")

    os.makedirs(TOKEN_DIR, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump({"refresh_token": tokens["refresh_token"]}, f)
    os.chmod(TOKEN_PATH, 0o600)
    print(f"Authorized. Refresh token saved to {TOKEN_PATH}")


def _access_token():
    _require_client_creds()
    if not os.path.isfile(TOKEN_PATH):
        sys.exit("Not authorized yet — run: python3 youtube_comment.py authorize")
    with open(TOKEN_PATH) as f:
        refresh_token = json.load(f)["refresh_token"]

    body = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, body, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def post_comment(video_id, text):
    """Posts `text` as a real top-level comment on `video_id`, on YOUR
    authorized YouTube account. Returns the created comment's id and URL."""
    access_token = _access_token()
    payload = json.dumps({
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {"snippet": {"textOriginal": text}},
        }
    }).encode()
    req = urllib.request.Request(
        COMMENT_URL,
        payload,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as err:
        detail = err.read().decode()
        sys.exit(f"YouTube API rejected the comment ({err.code}): {detail}")

    comment_id = result["id"]
    return {"comment_id": comment_id, "video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "authorize":
        authorize()
    elif cmd == "post":
        if len(sys.argv) < 4:
            sys.exit("usage: python3 youtube_comment.py post <video_id> \"<comment text>\"")
        result = post_comment(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))
    else:
        sys.exit(__doc__)
