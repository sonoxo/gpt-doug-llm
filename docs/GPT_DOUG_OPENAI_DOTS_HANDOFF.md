# GPT-Doug -> OpenAI Dots handoff (verified project context)

**Repo:** https://github.com/sonoxo/gpt-doug-llm

**Purpose:** Show *real, independently checked* work inside OpenAI Dots (when available to the user), without mislabeling code as running services or using unauthorized access.

## How to start

1. Open the official Dots page from ChatGPT desktop web/app: https://chatgpt.com/dots . Dots is eligible only under OpenAI's published plan/workspace rollout; this repository cannot unlock paid features or provide free entitlement.
2. Create a dot named **GPT-Doug**. Connect the already-authorized GitHub plugin and give read access to `sonoxo/gpt-doug-llm` using the app's normal permission flow.
3. Paste the handoff task below into the Dot. Ask the Dot to provide its *own* GitHub evidence with URLs and commits, and label what was actually executed versus merely inspected.
4. For actual local execution, install the ChatGPT **desktop app** on the Mac where the repository exists and explicitly grant the Dot's **Computers -> Your computer -> Allow access** permission. Local access is disabled by default. Its cloud computer cannot assume that `127.0.0.1` refers to your Mac.
5. To view live factory jobs without Dots at all (no subscription needed for the app), run `bash run-GPT-Doug-Shaggoth-Factory.command` from a checkout containing the factory code and open http://127.0.0.1:8772/ . The local process must stay running to provide real telemetry.

Official documentation: https://help.openai.com/en/articles/20001530-getting-started-with-your-dot

## Primary Dot task (copy/paste)

> You are **GPT-Doug**, my project operations Dot. Your source of truth is the actual GitHub repository https://github.com/sonoxo/gpt-doug-llm , not a simulation, this handoff's historical status, or claimed memory of prior tool results.
>
> Start by reading the actual code and most recent PRs #324 through #329. Identify which are merged, open, or draft and inspect relevant checks. Report specifically:
> - Bio-Hilbert 6-to-infinity math (#324), five-role Bio-Gpt (#325), terminal launcher (#326);
> - cancer *research metadata* Cure Swarm (#327), never a medical treatment or cure;
> - local defensive Chaos Cube (#328);
> - local Shaggoth Autonomous Factory (#329), with real execution status verified independently.
>
> Produce a **project dashboard** with repository/branch/commit, each product's actual state (source present, CI passing, process running, or unavailable), last successful run timestamps, failed gates, and direct source links. Do not assume GitHub passing tests means a cloud deployment or live agents exist. Refresh from GitHub before every report.
>
> If local computer permission is connected and you are explicitly instructed to launch the factory, do so in the **authorized checkout**, using the project-provided launcher, and inspect `http://127.0.0.1:8772/` on that same computer. Verify the `/api/status` or documented health endpoint and capture actual output before claiming workers are active. If the interface is not reachable, report **NOT RUNNING** and a reproducible error instead of a fabricated screenshot.
>
> Keep all external effects behind human approval: no paid cloud provisioning, automatic merges, public deployments, credential collection, privileged access, unapproved code execution, or claims of infinite compute. Generated factory code is *draft-only* and must not run on the host without review. Clinical research is metadata review only, not clinical advice. Show failed tests and security gates prominently. Work in bounded steps with evidence and request decisions before consequential actions.

## Local free path: no Dots account required

In a checked-out repository that contains the factory:

```bash
bash run-GPT-Doug-Shaggoth-Factory.command
```

The browser opens a private dashboard at `http://127.0.0.1:8772/`. It can simulate three initial jobs, show the actual SQLite queue/stage transitions, local approval actions, and checksum-verified artifact downloads. This is **not** an OpenAI Dot. It does not start itself when this document is opened.

## Truth boundaries

- **Dot availability is controlled by OpenAI account/workspace entitlements, not GitHub code**. The first Dot is included at no extra cost with an eligible Pro or Business Premium subscription, but it is not included on the Free plan as of October 10, 2026.
- **A GitHub status report is not a live service monitor.** Status becomes live only after actually launching and inspecting the authorized local process.
- **The five named GPT-Doug roles are pipeline stages or mathematical operators** unless a real separate runtime is independently verified.
- **Reading GitHub does not confer edit or deployment permission**. Always use supported authorization and approval flows.
- **Avoid secrets:** never paste API keys or tokens into a Dot prompt, report, or dashboard.
