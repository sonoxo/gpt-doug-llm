# 🛰️ GPT DOUG × Agents for Humans Hackathon — 10 Agent Build Plan

**Hackathon:** https://agentsforhumans.devpost.com/
**Deadline:** September 14, 2026 @ 5:00pm PDT
**Prize:** $40,000 cash (Grand Prize: $10,000)
**SDK:** Strands Agents SDK (AWS)
**Bonus:** Deploy on Amazon Bedrock AgentCore for higher Technical Implementation score
**Bonus:** Publish build story on builder.aws.com with "Agents for Humans" in title

---

## Three Tracks

| Track | Focus | Prize Pool |
|---|---|---|
| **Everyday Agents** | Daily life: home, money, health, errands, family | $10,000 (Gold/Silver/Bronze) |
| **Professional Agents** | Work: professionals, makers, creators, small-business | $10,000 (Gold/Silver/Bronze) |
| **Good Neighbor Agents** | Groups: neighborhoods, nonprofits, food banks, schools | $10,000 (Gold/Silver/Bronze) |
| **Grand Prize** | Best overall across all tracks | $10,000 + AWS meeting |

---

## Agent #1 — Zyra Sentinel Bot (Everyday Agents Track)
### Autonomous Home Network Security Monitor

**What it does:** Runs silently in the background on your home network. Scans for vulnerabilities, monitors IoT devices, detects unauthorized connections, and only surfaces when there's a real threat requiring a decision.

**Why it wins:**
- Uses Zyra Sentinel's existing scanning engine (ports, processes, DNS, SSL)
- Runs autonomously — only pings user when a threat needs human decision
- Strands Agents SDK wraps Sentinel's full_sweep() as an agent tool
- Deploy on AgentCore for continuous monitoring
- Real problem: 83% of homes have unsecured IoT devices

**Tech stack:** Strands Agents SDK, Amazon Bedrock AgentCore, Zyra Sentinel (existing), Twilio for alerts

---

## Agent #2 — Doug Document Drafter (Professional Agents Track)
### Autonomous Legal/Contract Review Agent

**What it does:** Small business owners upload contracts. The agent reads them, flags risky clauses, compares against industry standards, suggests edits, and generates a summary for the lawyer to review — cutting contract review from hours to minutes.

**Why it wins:**
- Real problem: small businesses can't afford $500/hr lawyers for every contract
- Agent runs end-to-end: read → analyze → flag → suggest → summarize
- Uses Zyra compliance gate for jurisdiction-aware risk assessment
- Only surfaces the 3-5 clauses that need human judgment
- Deploy on AgentCore with Bedrock LLM for document analysis

**Tech stack:** Strands Agents SDK, Amazon Bedrock (Claude for legal analysis), Zyra compliance gate (existing), web/ server (existing)

---

## Agent #3 — NeighborHelp Bot (Good Neighbor Agents Track)
### Autonomous Food Bank Inventory & Distribution Agent

**What it does:** Monitors food bank inventory in real-time. Predicts demand based on historical patterns, weather, and local events. Automatically orders restocks from partner grocers. Only pings the coordinator when there's a surplus shortage or unusual demand spike.

**Why it wins:**
- Real problem: 1 in 8 Americans use food banks; inventory management is manual
- Agent handles the repetitive inventory tracking autonomously
- Only surfaces when a real decision is needed (unusual demand, supply gap)
- Good Neighbor track — directly helps groups of people
- Uses agent_chain's planner→executor→reviewer pattern (existing)

**Tech stack:** Strands Agents SDK, Amazon Bedrock AgentCore, agent_chain (existing), Twilio for coordinator alerts

---

## Agent #4 — Zyra Meeting Sentinel (Everyday Agents Track)
### Autonomous Meeting Scheduler & Conflict Resolver

**What it does:** Watches your calendar. When a meeting request comes in, the agent checks for conflicts, proposes alternatives based on your preferences, automatically accepts/rejects based on rules you set, and only surfaces when there's an ambiguous conflict requiring human judgment.

**Why it wins:**
- Repetitive task: scheduling is the #1 time waster for knowledge workers
- Runs in background — only surfaces for genuine conflicts
- Uses Zyra to redact sensitive meeting details from the agent's context
- Integrates Google Calendar API via Strands Agents SDK tool calling

**Tech stack:** Strands Agents SDK, Google Calendar API, Bedrock AgentCore, Zyra (existing for PII redaction)

---

## Agent #5 — Doug Health Tracker (Everyday Agents Track)
### Autonomous Medication & Appointment Manager

**What it does:** Tracks medication schedules, reminds at the right time, automatically books refills from the pharmacy, schedules doctor appointments when refills run low, and only surfaces when there's a drug interaction warning or appointment conflict needing a decision.

**Why it wins:**
- 50% of Americans take prescription medications; 50% don't take them correctly
- Agent handles the repetitive refill/appointment booking autonomously
- Only surfaces for real health decisions (interactions, conflicts)
- Compliance gate ensures it never gives medical advice — just logistics
- HIPAA-conscious: Zyra redacts all health data from agent logs

**Tech stack:** Strands Agents SDK, Bedrock AgentCore, Zyra (existing for data protection), Twilio for reminders

---

## Agent #6 — Zyra Invoice Ninja (Professional Agents Track)
### Autonomous Freelancer Invoice & Payment Chaser

**What it does:** For freelancers and small businesses. Automatically generates invoices from tracked hours, sends them to clients, follows up on overdue payments with escalating reminders, and only surfaces the human when a client disputes or a payment fails.

**Why it wins:**
- 38% of freelancer invoices are paid late — this chases them automatically
- Agent handles the full cycle: track → invoice → send → remind → escalate
- Only surfaces for disputes or payment failures (real human decisions)
- Uses web/stripe_checkout.py (existing) for payment processing
- Good revenue case: saves freelancers 5+ hours/month

**Tech stack:** Strands Agents SDK, Stripe API (existing integration), Bedrock AgentCore, web platform (existing)

---

## Agent #7 — Community Emergency Mesh (Good Neighbor Agents Track)
### Autonomous Neighborhood Emergency Coordinator

**What it does:** Monitors weather alerts, power outage reports, and emergency broadcasts. When a threat is detected for a neighborhood, the agent automatically coordinates: sends alerts to registered neighbors, checks on elderly/vulnerable residents, compiles status reports, and only surfaces the coordinator when resources need allocation decisions.

**Why it wins:**
- Good Neighbor track — helps entire neighborhoods, not just one person
- Real problem: during 2023 ice storm in Texas, 246 died from lack of coordination
- Agent runs the coordination loop autonomously (alert → check → compile → report)
- Only surfaces for resource allocation (generators, transportation, medical)
- Uses Sentinel's external feed monitoring (existing) for weather/alerts

**Tech stack:** Strands Agents SDK, Bedrock AgentCore, Zyra Sentinel feeds (existing), Twilio for neighborhood alerts

---

## Agent #8 — Doug Code Reviewer (Professional Agents Track)
### Autonomous PR Review & Security Gate Agent

**What it does:** Watches your GitHub repo. When a PR is opened, the agent automatically reviews the code: runs tests, checks for security vulnerabilities using Zyra patterns, verifies style compliance, and only surfaces the maintainer when there's a genuine judgment call (design decision, ambiguous bug).

**Why it wins:**
- Uses gpt-doug-llm's existing agent_chain (planner→executor→reviewer) pattern
- Zyra's existing security patterns for vulnerability detection in code
- GitHub webhook integration via existing web/server.py
- Only surfaces for real judgment — everything else is autonomous
- Deploy on AgentCore for 24/7 monitoring

**Tech stack:** Strands Agents SDK, GitHub API, Bedrock AgentCore, agent_chain (existing), Zyra (existing), web/server.py (existing)

---

## Agent #9 — Zyra Expense Sentinel (Everyday Agents Track)
### Autonomous Receipt Scanner & Expense Categorizer

**What it does:** Watches your email for receipts. Automatically extracts amount, merchant, date, and category. Categorizes expenses, tracks against budget, flags anomalies, and only surfaces when there's an unusual charge or budget threshold exceeded.

**Why it wins:**
- Repetitive task: the average person loses 2+ hours/month on expense tracking
- Agent handles the full cycle: scan → extract → categorize → budget → flag
- Only surfaces for anomalies (unusual spending, budget warnings)
- Zyra redacts financial data from agent context (existing DLP)
- Can export to QuickBooks, Mint, or YNAB via API

**Tech stack:** Strands Agents SDK, Gmail API, Bedrock AgentCore, Zyra DLP (existing for financial data protection)

---

## Agent #10 — Doug School Coordinator (Good Neighbor Agents Track)
### Autonomous School Volunteer & Event Coordinator

**What it does:** For schools and PTAs. Automatically matches parent volunteers to needed roles, sends reminders, tracks volunteer hours, coordinates event logistics (food, supplies, setup), and only surfaces the coordinator when there's a gap that needs human recruitment.

**Why it wins:**
- Good Neighbor track — directly helps schools and parent communities
- Real problem: 75% of PTA volunteer coordination is manual email chains
- Agent handles matching, reminding, tracking autonomously
- Only surfaces when there's a gap (no volunteer for a critical role)
- Uses worker/agent-daemon.py's task queue pattern (existing)

**Tech stack:** Strands Agents SDK, Bedrock AgentCore, agent-daemon task queue (existing), Twilio for reminders

---

## Strategic Submission Plan

### Primary Submission: Agent #8 — Doug Code Reviewer
**Why this is our best shot at Grand Prize:**
- We already have the code (agent_chain + Zyra + GitHub webhook server)
- Most technically impressive (security + code review + autonomy)
- Uses existing 7,177 lines of code as the foundation
- Clear demo: open a PR → agent reviews it autonomously → surfaces only the judgment calls
- Deploy on AgentCore for 24/7 GitHub monitoring
- Architecture diagram already exists in docs/

### Secondary Submission: Agent #1 — Zyra Sentinel Bot
**Why this could win Everyday Agents:**
- We already have the full Sentinel scanner (1,407 lines)
- Unique: no other competitor has a security scanner for home networks
- Clear demo: scan home network → find vulnerabilities → alert only on threats
- 10,000+ homes have vulnerable IoT — immediate impact story

### Tertiary Submission: Agent #7 — Community Emergency Mesh
**Why this could win Good Neighbor:**
- Sentinel's existing external feed monitoring + Twilio calling (existing)
- Emotional impact: saves lives during emergencies
- Clear demo: simulate weather alert → agent coordinates neighborhood response
- Good Neighbor track has fewer competitors — easier to place

---

## What We Already Have (Advantage)

| Existing Asset | Hackathon Use |
|---|---|
| Zyra 3.0 watchdog | Security for every agent (PII redaction, threat detection) |
| Golden Shield | Perimeter defense for deployed agents |
| Sentinel 24/7 scanner | Home network monitoring (Agent #1) |
| agent_chain.py | Planner→Executor→Reviewer for all agents |
| web/server.py | Webhook receiver for GitHub, Twilio, Stripe |
| compliance.py | Jurisdiction-aware policy for health/legal agents |
| ontology.py + knowledge base | Domain knowledge for all agents |
| worker/agent-daemon.py | Task queue for autonomous agents |
| EUREKA protocol | Inter-agent communication |
| 113 tests | Proof of quality for judges |
| MIT license | Required by hackathon |

## What We Need to Build

1. **Strands Agents SDK integration** — wrap existing modules as Strands tools
2. **AgentCore deployment** — deploy to AWS Bedrock AgentCore
3. **Architecture diagram** — for submission requirements
4. **Demo video** (5 min max) — show agent running end-to-end
5. **builder.aws.com post** — bonus points for build story

## Timeline

| Week | Task |
|---|---|
| 1 | Strands SDK integration — wrap Zyra, Sentinel, agent_chain as Strands tools |
| 2 | Build Agent #8 (Code Reviewer) — GitHub webhook → Strands → Zyra → review |
| 3 | Build Agent #1 (Sentinel Bot) — deploy Sentinel on AgentCore |
| 4 | Build Agent #7 (Emergency Mesh) — Twilio + Sentinel feeds |
| 5 | Demo videos, architecture diagrams, README polish |
| 6 | Submit to Devpost + publish on builder.aws.com |

## $40,000 is on the table. We already have the code. Let's build.
