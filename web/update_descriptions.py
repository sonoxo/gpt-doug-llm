#!/usr/bin/env python3
"""One-off: append a promo line to every video's existing YouTube
description, linking to the paid agent-task page. Only touches
description — fetches the full current snippet first and preserves
everything else (title, categoryId, tags, etc.) since YouTube's
videos.update requires the whole snippet object, not a partial patch."""
import json
import sys
import urllib.error
import urllib.request

import youtube_comment

PROMO = "\n\n---\n🤖 Get an AI agent to complete any task for $1: https://afford-cedar-aptly.ngrok-free.dev/buy"

with open("all_video_ids.json") as f:
    video_ids = json.load(f)

access_token = youtube_comment._access_token()
results = []

for vid in video_ids:
    req = urllib.request.Request(
        f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={vid}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    items = data.get("items", [])
    if not items:
        results.append({"video_id": vid, "status": "not_found"})
        continue

    snippet = items[0]["snippet"]
    if "🤖 Get an AI agent" in snippet.get("description", ""):
        results.append({"video_id": vid, "status": "skipped_already_has_promo"})
        print(f"--- skip {vid} (already promoted) ---", file=sys.stderr)
        continue

    snippet["description"] = (snippet.get("description") or "") + PROMO

    body = json.dumps({"id": vid, "snippet": snippet}).encode()
    req = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/videos?part=snippet",
        data=body,
        method="PUT",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            json.loads(resp.read())
        results.append({"video_id": vid, "status": "updated"})
        print(f"--- updated {vid} ---", file=sys.stderr)
    except urllib.error.HTTPError as err:
        detail = err.read().decode()
        results.append({"video_id": vid, "status": "failed", "error": detail[:300]})
        print(f"--- failed {vid}: {detail[:200]} ---", file=sys.stderr)

    with open("update_descriptions_output.json", "w") as f:
        json.dump(results, f, indent=2)

print(json.dumps(results, indent=2))
