# Devpost Submission — GPT Doug × Agents for Humans

## Project Name
GPT Doug LLM — Autonomous AI Agents with Built-in Cybersecurity

## One-liner
10 autonomous AI agents that handle repetitive tasks — built on an open-source security stack with a 24/7 threat intelligence scanner, zero-budget deployment, and a "only surface when needed" philosophy.

## Full Description

### The Problem
Most AI agents are built without security. They handle sensitive data with no guardrails, no audit trail, no threat detection. And they surface the human for every trivial decision, defeating the purpose of autonomy.

### Our Solution
GPT Doug LLM is an open-source local-first agentic AI system with a defense-in-depth security architecture. We built 10 autonomous agents for 3 hackathon tracks, each using our existing security stack:

**Zyra 3.0 Watchdog** — Inspects every input and output for security threats. Redacts secrets, blocks destructive commands, detects social engineering (RICE framework), classifies sensitivity, and writes tamper-evident HMAC-chained audit logs.

**Golden Shield** — Perimeter defense that eliminates threats before they reach any agent. Rate limiting, flood detection, source banning, and 14 threat elimination patterns (botnet, reverse shell, cryptominer, rootkit, supply chain attack, container escape).

**Zyra Sentinel** — 24/7 vulnerability scanner. Scans internally (ports, processes, files, DNS, SSL, cron, dependencies), externally (NIST NVD CVEs, CISA KEV, GitHub advisories), satellite/orbital (CelesTrak/NORAD), and dark web exposure. Runs continuously on a background thread.

### The 10 Agents

**Everyday Agents:** Home network security scanner, calendar conflict resolver, medication manager, expense tracker

**Professional Agents:** Contract reviewer, freelance invoice chaser, autonomous PR code reviewer ★

**Good Neighbor Agents:** Food bank inventory coordinator, neighborhood emergency coordinator, school volunteer matcher

### "Only Surface When Needed"
Every agent runs autonomously and only surfaces the human when there's a genuine judgment call. The security scanner only alerts on CRITICAL findings. The code reviewer only flags the maintainer for ambiguous bugs. The invoice chaser only escalates unresponsive clients after 14 days.

### Built on Free Resources ($0 Budget)
- GitHub Actions (free for public repos)
- AWS Lambda free tier (1M requests/month)
- Cloudflare Workers (100K requests/day)
- Streamlit Cloud (free hosting)
- Ollama (free local LLM)

### The Numbers
- 14,849 lines of code
- 140 files
- 103 tests passing
- 173 knowledge base entries
- MIT licensed
- 39 commits

## Architecture
```
User/Agent → Golden Shield → Zyra 3.0 → Compliance Gate → Agent Chain → Output Sterilize → User
                    ↓                                    ↓
              Sentinel Scanner                    Knowledge Base (173 entries)
              (24/7 monitoring)                   (IBM, CIA, FBI, MIT, TechForce)
```

## How We Built It
We started with gpt-doug-llm — an existing open-source local-first AI terminal client. We then:
1. Merged 5 agentic LLM projects into one unified system
2. Built the Golden Shield perimeter defense (1,407 lines)
3. Added the Sentinel 24/7 scanner (internal + external + satellite + dark web)
4. Created 10 agents using the existing security stack
5. Wrapped everything as Strands SDK tools
6. Deployed on free infrastructure ($0 budget)

## Challenges We Ran Into
- Unicode evasion attacks (Cyrillic homoglyphs, zero-width spaces) required dual-normalization
- Concurrent audit logging required thread-safe HMAC chaining
- Balancing autonomy with safety — knowing when to surface the human
- Zero-budget deployment required creative use of free tiers

## Accomplishments
- 103 tests covering security patterns, evasion attacks, and agent logic
- 125-payload DDoS simulation: 100% attack block rate, 0% false positives
- 173-entry knowledge base with proper attribution
- 10 working agents across 3 tracks

## What We Learned
Security is a feature, not an add-on. Agents that redact PII, block threats, and audit decisions are more valuable than agents that don't. And "agents for humans" means handling the repetitive work so humans only make the decisions that matter.

## What's Next
- Deploy Code Reviewer on Amazon Bedrock AgentCore
- Integrate with real GitHub webhooks
- Add more knowledge domains
- Publish build story on builder.aws.com

## Built With
Python, Ollama, Strands Agents SDK, GitHub Actions, AWS Lambda, Cloudflare Workers, Streamlit, Twilio, Stripe, MIT License
