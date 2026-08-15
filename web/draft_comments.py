#!/usr/bin/env python3
"""One-off batch: run the agent chain once per video to draft a genuinely
varied, tailored YouTube comment for each. Writes drafts to
draft_comments_output.json for human review — never posts anything itself."""
import json
import sys

import agent_chain

VIDEOS = [
    ("yLPQyJwtims", "#UNIVERSE #QUANTUM #META #METAPHYSICAL #UNI #PHY #PSY #SCI #almightysonoxo #growthanddevelopment #3"),
    ("qb_BC7tQJq8", "META FACEBOOK INSTA SOCIAL - #growthanddevelopment #knowledgeispower #almightysonoxo #Study #Read74"),
    ("AW61IQzPGOo", "#KUNDALINI #mahamantra #almightysonoxo #growthanddevelopment #musician #777hz"),
    ("4dzMcQqNFZE", "TAKE YOUR #energy back #Formula #almightysonoxo #oeglobal #TheHealingInstitue"),
    ("I0u3k70L_fE", "You are only as great as YOU want to be #AlmightySpeaks"),
]

results = []
for video_id, title in VIDEOS:
    task = (
        f"Write ONE short YouTube comment (under 200 characters, no hashtag spam, "
        f"no emoji spam, sound like a real person not marketing copy) as the artist "
        f"Almighty Sonoxo, reflecting genuinely on their own post titled: \"{title}\". "
        f"Make it distinct in wording and angle from a typical generic hype comment."
    )
    print(f"--- drafting for {video_id} ---", file=sys.stderr)
    trace = agent_chain.run(task)
    # last execute_done event holds the final drafted text
    executes = [e for e in trace["events"] if e["stage"] == "execute_done"]
    draft = executes[-1]["output"] if executes else ""
    results.append({"video_id": video_id, "title": title, "draft": draft, "run_id": trace["run_id"]})
    with open("draft_comments_output.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"--- done {video_id}: {draft[:80]} ---", file=sys.stderr)

print(json.dumps(results, indent=2))
