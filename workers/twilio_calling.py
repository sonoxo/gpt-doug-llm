"""
Copyright (c) 2026 Douglas Brown Jr / Xuniaverse. Licensed under the
xuniaverse-production LICENSE (All Rights Reserved).

Real outbound calling via Twilio's Voice API.

STATUS: unverified. No Twilio account/credentials exist yet as of the
commit that added this file -- this has NOT been tested against a real
call. Do not treat "code is written" as "calling works" until this has
actually been exercised against a live Twilio account and this notice
is removed/updated.

Requires: pip install twilio
Requires real credentials, set as environment variables (never hardcode
them, never commit them):
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_FROM_NUMBER   (the Twilio number you purchased, E.164 format e.g. +15551234567)
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zyra_guard  # noqa: E402

# E.164 format: + followed by 8-15 digits. Real validation, not decorative --
# Twilio will reject malformed numbers, but failing fast here with a clear
# error is better than a confusing API error later.
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


class CallError(Exception):
    pass


def _get_client():
    """Import and construct the Twilio client lazily -- importing this
    module must not require the twilio package or credentials to be
    present, same lazy-resolution lesson learned from CLAUDE_BIN earlier
    in this project (that bug broke CI when resolution happened at import
    time instead of at call time)."""
    try:
        from twilio.rest import Client
    except ImportError:
        raise CallError("twilio package not installed — run: pip install twilio")

    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    if not sid or not token or not from_number:
        raise CallError(
            "Missing Twilio credentials. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "and TWILIO_FROM_NUMBER as environment variables."
        )
    if not _E164_RE.match(from_number):
        raise CallError(f"TWILIO_FROM_NUMBER {from_number!r} is not valid E.164 format (e.g. +15551234567)")

    return Client(sid, token), from_number


def place_call(to_number: str, message: str, task_id: str = "twilio-call") -> dict:
    """
    Places a real outbound call that speaks `message` via text-to-speech.

    Routed through zyra_guard.review() first, same as every other action
    in this project — a call is a real-world, costly, hard-to-take-back
    action, so it gets the same pre-flight review as a task dispatch, not
    a bypass just because it's a different action type.
    """
    if not _E164_RE.match(to_number or ""):
        raise CallError(f"to_number {to_number!r} is not valid E.164 format (e.g. +15551234567)")
    if not message or not isinstance(message, str):
        raise CallError("message must be a non-empty string")

    allowed, reason = zyra_guard.review({"id": task_id, "prompt": message})
    if not allowed:
        raise CallError(f"rejected by zyra_guard: {reason}")

    client, from_number = _get_client()

    # TwiML: minimal, escapes the message via Twilio's own Say verb (the
    # SDK handles XML escaping) so no manual string-building into markup.
    from twilio.twiml.voice_response import VoiceResponse
    twiml = VoiceResponse()
    twiml.say(message)

    call = client.calls.create(to=to_number, from_=from_number, twiml=str(twiml))
    return {"call_sid": call.sid, "to": to_number, "from": from_number, "status": call.status}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 twilio_calling.py <to_number_E164> <message>")
        print("Example: python3 twilio_calling.py +15551234567 'Hello from Doug'")
        sys.exit(1)
    result = place_call(sys.argv[1], " ".join(sys.argv[2:]))
    print(result)
