"""Twilio SMS webhook support: request signature validation and TwiML replies.

No twilio SDK dependency — the signature check is the same HMAC-SHA1 scheme
Twilio documents (https://www.twilio.com/docs/usage/security#validating-requests),
implemented directly against stdlib hmac/hashlib so this stays self-contained.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import parse_qsl
from xml.sax.saxutils import escape


def parse_form(raw: bytes) -> dict:
    return dict(parse_qsl(raw.decode("utf-8", errors="replace"), keep_blank_values=True))


def validate_signature(auth_token: str, url: str, params: dict, signature: str) -> bool:
    """Recompute Twilio's X-Twilio-Signature and compare in constant time.

    Twilio's scheme: sort the POST params by key, concatenate
    "key" + "value" for each onto the full request URL, then HMAC-SHA1
    that string with the auth token and base64-encode it.
    """
    if not signature:
        return False
    data = url
    for key in sorted(params.keys()):
        data += key + params[key]
    digest = hmac.new(auth_token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def twiml_message(body: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(body)}</Message></Response>"
    ).encode("utf-8")


def twiml_empty() -> bytes:
    return b'<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
