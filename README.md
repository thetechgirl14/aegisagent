# 🛡️ AegisAgent

> **Real-time, multi-layer security middleware for agentic AI pipelines.**
>
> *Microsoft Build AI 2026 — Track: Security in the Agentic Future*

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-34d399?style=flat-square)](https://aegisagent-thetechgirl.streamlit.app/)
 [![YouTube](https://img.shields.io/badge/Demo%20Video-YouTube-red?style=flat-square)](https://youtu.be/UCYdxbto3uU)
 [![GitHub](https://img.shields.io/badge/GitHub-thetechgirl14%2Faegisagent-blue?style=flat-square)](https://github.com/thetechgirl14/aegisagent)
 [![Python](https://img.shields.io/badge/Python-3.11+-yellow?style=flat-square)](https://python.org)
 [![Azure OpenAI](https://img.shields.io/badge/Azure-OpenAI-0078d4?style=flat-square)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)

**[→ Try the live interactive demo](https://aegisagent-thetechgirl.streamlit.app/)** — no login, no setup. Click "Run Benign Session", then "Inject Attack" and watch all three layers respond in real time.

**[→ Watch the demo video](https://youtu.be/UCYdxbto3uU)**

---

## The Problem

AI agents are powerful — but they are new attack surfaces. As autonomous systems start making decisions, browsing the web, and orchestrating other agents, three new threats emerge that traditional input validation cannot handle:

- **Prompt injection** — malicious payloads hidden inside tool responses or chained agent messages
- **Semantic drift** — gradual multi-turn manipulation that steers an agent toward a malicious goal
- **Tool escalation** — an agent invoking capabilities it was never granted

Traditional input validation was built for forms. It doesn't understand conversation context, sliding windows of behavior, or the difference between a clean tool call and an adversarially crafted one.

---

## Solution

AegisAgent is a **drop-in security middleware layer** that wraps any Azure OpenAI multi-agent pipeline without modifying agent logic. It intercepts every message and tool call through three concentric defense layers, quarantines threats, and rolls back state to the last clean checkpoint — all in real time.

- **Zero modification** required to existing agent code
- **< 50 ms** added latency on the synchronous hot path
- **Instant rollback** to last known-clean agent state (L3)
- **Full audit trail** for compliance and incident response

---

## Architecture

```
User / Upstream Agent
        │
        ▼
┌───────────────────────────────────┐
│  L1: Synchronous Gate  (< 50 ms) │  ← inline, every message & tool call
│  • Length check (O(1))            │
│  • 26 compiled regex patterns     │
│  • Azure AI Content Safety        │
│    (Prompt Shield + analyze_text) │
└──────────────┬────────────────────┘
               │ PASS → enqueue metadata
               ▼
┌──────────────────────────────────────────┐
│  L2: Stateful Evaluator  (async)         │  ← non-blocking background consumer
│  • Sliding window: last 5 turns          │
│  • Azure OpenAI GPT-4o-mini as judge     │
│  • Pydantic-validated L2SecurityVerdict: │
│    threat_detected | confidence_score    │
│    vulnerability_type | action_required  │
│  → HALT signal triggers L3              │
└──────────────┬───────────────────────────┘
               │ HALT
               ▼
┌──────────────────────────────────────────┐
│  L3: State Ledger + Rollback             │  ← checkpoint / quarantine / recover
│  • Immutable checkpoint deque            │
│  • quarantine_and_rollback():            │
│    1. Remove offending agent's turn      │
│    2. Spawn fresh agent from factory     │
│    3. Resume from T-1 clean checkpoint   │
└──────────────────────────────────────────┘
```

---

## Azure & AI Services Used

| Service | Role in AegisAgent |
|---|---|
| **Azure OpenAI GPT-4o-mini** | L2 stateful security evaluator — analyses a sliding window of the last 5 turns and returns a structured `L2SecurityVerdict` |
| **Azure AI Content Safety** | L1 Prompt Shield (primary) + `analyze_text` fallback — live API calls for injection and jailbreak detection |
| **Pydantic v2** | Strict schema validation of AI security verdicts — no untyped AI output enters the pipeline |
| **Python asyncio** | Non-blocking L2 evaluation so security never touches the hot path latency |
| **Streamlit** | Real-time operator console — live telemetry, fidelity dial, audit ledger, attack simulator |

---

## Project Structure

```
aegisagent/
├── agent_framework/          # Self-owned Azure OpenAI agent SDK (no third-party dependency)
│   ├── core.py               #   Agent class with tool-calling loop
│   └── openai.py             #   AsyncAzureOpenAI chat client wrapper
├── aegis_interceptor.py      # L1 synchronous gate — length, regex, Azure Content Safety
├── aegis_l2_engine.py        # L2 async stateful evaluator — sliding window + GPT-4o-mini judge
├── aegis_state_manager.py    # L3 checkpoint ledger + quarantine/rollback
├── app_agents.py             # Full pipeline: two-agent orchestration wrapped by AegisAgent
├── dashboard.py              # Streamlit operator console (runs standalone — no Azure needed)
├── tests/
│   └── test_aegis.py         # 21 unit tests covering L1 patterns, interceptors, L3 rollback
└── requirements.txt
```

---

## Running Locally

```bash
git clone https://github.com/thetechgirl14/aegisagent.git
cd aegisagent
pip install -r requirements.txt

# Launch the dashboard (no Azure credentials needed)
streamlit run dashboard.py

# Run the full security pipeline against real Azure OpenAI
cp .env.example .env   # add your Azure keys
python app_agents.py

# Run tests
pytest tests/ -v
```

---

## Team

| | |
|---|---|
| **Name** | Abhilasha Jain |
| **Team** | TheTechGirl |
| **Role** | Solo — Architecture, Security Design, Full-Stack |
| **GitHub** | [github.com/thetechgirl14](https://github.com/thetechgirl14) |
| **Hackathon** | Microsoft Build AI 2026 — Track: Security in the Agentic Future |
