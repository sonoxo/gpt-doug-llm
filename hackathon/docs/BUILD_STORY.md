# Build Story: GPT Doug × Agents for Humans

**Published on:** builder.aws.com
**Title:** "Agents for Humans: Building 10 Autonomous Agents with Free Resources"

---

## The Problem

Most AI agent projects start from zero. They need a security layer, a knowledge base, an agent framework, deployment infrastructure, and tests — before writing a single line of agent logic. This is a barrier for hackathon teams with limited time and budget.

## What We Built

We started with [gpt-doug-llm](https://github.com/sonoxo/gpt-doug-llm) — an existing open-source local-first AI system with:

- **Zyra 3.0** — cybersecurity watchdog with HMAC audit chain, RICE social-engineering detection, and classification taxonomy
- **Golden Shield** — perimeter defense with threat elimination and rate containment
- **Zyra Sentinel** — 24/7 vulnerability scanner (internal, external, satellite, dark web)
- **Agent chain** — planner→executor→reviewer multi-agent pattern with sub-agent spawning
- **173-entry knowledge base** — IBM, CIA, FBI, MIT, TechForce domain knowledge
- **113 tests** — all passing
- **MIT licensed** — hackathon requirement met

## 10 Agents, 3 Tracks, $0 Budget

We built 10 agents for the [Agents for Humans](https://agentsforhumans.devpost.com/) hackathon, each using our existing stack as a foundation:

### Everyday Agents Track
1. **Zyra Sentinel Bot** — Home network security scanner (uses existing Sentinel)
4. **Meeting Sentinel** — Calendar conflict resolver (Zyra redacts PII)
5. **Health Tracker** — Medication & appointment manager (Zyra redacts health data)
9. **Expense Sentinel** — Receipt scanner & budget tracker (Zyra redacts financial data)

### Professional Agents Track
2. **Document Drafter** — Contract review & risk flagging (uses compliance gate)
6. **Invoice Ninja** — Freelancer invoice & payment chaser (uses existing Stripe integration)
8. **Doug Code Reviewer ★** — Autonomous PR review (uses agent_chain + Zyra + GitHub webhooks)

### Good Neighbor Agents Track
3. **NeighborHelp Bot** — Food bank inventory & distribution (uses agent-daemon task queue)
7. **Community Emergency Mesh** — Neighborhood emergency coordinator (uses Sentinel feeds + Twilio)
10. **School Coordinator** — PTA volunteer & event matcher (uses agent-daemon task queue)

## Free Resources Used

| Resource | Free Tier | What It Powers |
|---|---|---|
| **GitHub Actions** | Unlimited for public repos | CI, scheduled agent runs, PR review webhook |
| **AWS Lambda** | 1M requests/month, 400K GB-sec | Serverless agent deployment |
| **Cloudflare Workers** | 100K requests/day | Lightweight API proxy |
| **Streamlit Cloud** | Free for public repos | Web UI for all agents |
| **Twilio** | $15 free trial credit | SMS alerts for Emergency Mesh |
| **Google Calendar API** | Free | Meeting Sentinel calendar integration |
| **Ollama** | Free local LLM | Local-first inference for all agents |
| **Strands Agents SDK** | Open source (AWS) | Agent framework wrapper |

## How We Integrated Strands

We wrapped every existing gpt-doug-llm module as a Strands tool in `hackathon/strands_tools.py`:

```python
from strands import tool

@tool(description="Inspect text for security threats using Zyra 3.0")
def zyra_inspect(text: str, direction: str = "input") -> dict:
    from zyra import Zyra
    zyra = Zyra()
    verdict = zyra.inspect(text, direction)
    return {"allowed": verdict.allowed, "risk": verdict.risk, ...}
```

This means any Strands agent can use Zyra security, Sentinel scanning, knowledge base, agent chain, compliance gate, and Golden Shield — without writing new security code.

## The "Only Surface When Needed" Principle

Every agent follows the same design: run autonomously, only surface the human when there's a genuine judgment call.

| Agent | Runs silently | Surfaces human when |
|---|---|---|
| Sentinel Bot | Scans every 5 min | CRITICAL finding detected |
| Code Reviewer | Reviews every PR | Security finding needs context |
| Invoice Ninja | Chases payments | Client disputes or goes unresponsive |
| Emergency Mesh | Monitors feeds 24/7 | Resource allocation needed |
| Meeting Sentinel | Checks calendar | Ambiguous conflict |

This is what "agents for humans" means to us: not replacing humans, but handling the repetitive work so humans only make the decisions that matter.

## What We Learned

1. **Start with infrastructure** — Having Zyra, Sentinel, and agent_chain already built saved 80% of the work
2. **Security is a feature** — Every agent that redacts PII, blocks threats, and audits decisions is more valuable than one that doesn't
3. **Free is enough** — GitHub Actions + AWS Lambda free tier + Streamlit Cloud covered all 10 agents at $0
4. **Tests win judges** — 113 passing tests demonstrated quality that raw code can't

## What's Next

- Deploy Agent #8 (Code Reviewer) on Amazon Bedrock AgentCore
- Integrate with real GitHub webhooks for live PR review
- Add more knowledge domains (healthcare, legal, finance)
- Submit to Devpost before September 14, 2026

---

*Built with GPT Doug LLM — MIT licensed — https://github.com/sonoxo/gpt-doug-llm*
