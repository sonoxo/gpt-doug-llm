"""Example: use the Pineal API to read/write external AI context, NOT model weights."""
import json
import os
from urllib.request import Request, urlopen

base = "http://127.0.0.1:8765"
token = os.environ["PINEAL_TOKEN"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {"namespace": "projects", "subject": "gpt-doug-pineal",
           "predicate": "mission", "value": "Audit external memory edits",
           "source": "user-approved CLI example", "confidence": 1.0}
req = Request(f"{base}/v1/memories", method="POST", headers=headers,
              data=json.dumps(payload).encode("utf-8"))
with urlopen(req, timeout=5) as result:
    print("Write:", json.load(result))
req = Request(f"{base}/v1/context?q=mission", headers=headers)
with urlopen(req, timeout=5) as result:
    print("Read:", json.load(result))
