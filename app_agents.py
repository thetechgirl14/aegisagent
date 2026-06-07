import asyncio
import json
import os
from typing import Any, Dict

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from aegis_interceptor import AegisInterceptor, AegisSecurityException
from aegis_l2_engine import L2_Stateful_Evaluator
from aegis_state_manager import AegisStateLedger

from dotenv import load_dotenv
import os

load_dotenv()

def create_azure_chat_client() -> OpenAIChatClient:
    """Build the Azure OpenAI chat client using enterprise environment bindings."""
    return OpenAIChatClient(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )


def fetch_unstructured_financial_data() -> Dict[str, Any]:
    """Local mock tool payload for unstructured financial data."""
    return {
        "metadata": {
            "source": "local-mock",
            "snapshot_time": "2026-05-29T09:00:00Z",
            "region": "global",
        },
        "market_snapshot": {
            "equities": [
                {
                    "symbol": "SPX",
                    "close": 5430.12,
                    "change_pct": -0.82,
                    "comment": "Large-cap technology weakness pressured the benchmark.",
                },
                {
                    "symbol": "FTSE",
                    "close": 7620.55,
                    "change_pct": 0.38,
                    "comment": "Energy and financials led a modest rally.",
                },
            ],
            "rates": {
                "10y_treasury": 4.67,
                "fed_funds": 5.25,
                "policy_outlook": "pause expected",
            },
        },
        "company_signals": [
            {
                "ticker": "ABCD",
                "signal": "revenue_miss",
                "impact": "negative",
                "sector": "Consumer",
            },
            {
                "ticker": "EFGH",
                "signal": "margin_expansion",
                "impact": "positive",
                "sector": "Industrial",
            },
        ],
        "risk_indicators": {
            "credit_spread_bps": 405,
            "liquidity_index": "stable",
            "geopolitical_risk": "moderate",
        },
    }


async def fetch_financial_data_tool() -> Dict[str, Any]:
    """Tool wrapper isolated from agent orchestration for future hook-ins."""
    return await asyncio.to_thread(fetch_unstructured_financial_data)


def build_data_retriever_agent(client: OpenAIChatClient, interceptor: AegisInterceptor) -> Agent:
    """Define the Data_Retriever_Agent with a dedicated data tool and interceptor wrapper."""
    return Agent(
        client=client,
        name="Data_Retriever_Agent",
        instructions=(
            "You are Data_Retriever_Agent. Use the attached tool to fetch the unstructured "
            "financial payload, and return the result as a clean JSON-like data structure. "
            "Do not add analysis or narrative in this step; only return the structured raw data."
        ),
        tools=[interceptor.wrap_tool("FinancialDataFetcher", fetch_financial_data_tool)],
    )


def build_analyst_agent(client: OpenAIChatClient) -> Agent:
    """Define the Analyst_Agent for trend summarization and markdown reporting."""
    return Agent(
        client=client,
        name="Analyst_Agent",
        instructions=(
            "You are Analyst_Agent. Receive raw financial data payloads from Data_Retriever_Agent, "
            "summarize market trends, highlight risk signals, and produce a polished markdown report "
            "with an executive summary, key findings, and recommended next steps."
        ),
    )


async def run_data_retriever(agent: Agent, interceptor: AegisInterceptor) -> str:
    """Route the retriever prompt through the interceptor and into the agent."""
    prompt = (
        "Use the data tool to fetch the latest unstructured financial dataset. "
        "Return the payload in a JSON-compatible format with no extra explanation."
    )
    return await interceptor.route_agent_request(agent, prompt)


async def run_analyst(agent: Agent, interceptor: AegisInterceptor, raw_payload: str) -> str:
    """Route the analyst prompt through the interceptor and produce markdown."""
    prompt = (
        "The following raw financial payload was produced by Data_Retriever_Agent. "
        "Summarize the most important trends, risk indicators, and opportunities, "
        "and format the output as a markdown report.\n\n"
        f"Raw payload:\n{raw_payload}"
    )
    return await interceptor.route_agent_request(agent, prompt)


async def run_chat_loop() -> None:
    metadata_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    stop_event = asyncio.Event()

    interceptor = AegisInterceptor(metadata_queue=metadata_queue)
    client = create_azure_chat_client()
    evaluator = L2_Stateful_Evaluator(
        client=client,
        metadata_queue=metadata_queue,
        stop_event=stop_event,
    )
    ledger = AegisStateLedger()

    retriever_agent = build_data_retriever_agent(client, interceptor)
    analyst_agent = build_analyst_agent(client)

    await ledger.register_agent_factory(
        retriever_agent.name,
        lambda: build_data_retriever_agent(client, interceptor),
    )
    await ledger.register_agent_factory(
        analyst_agent.name,
        lambda: build_analyst_agent(client),
    )

    current_context: Dict[str, Any] = {}
    current_cycle = 0
    while True:
        current_cycle += 1
        if current_cycle > 3:
            print("[ERROR] Recovery loop exceeded safe limit. Aborting.")
            break

        try:
            print("[INFO] Running Data_Retriever_Agent...")
            raw_payload = await run_data_retriever(retriever_agent, interceptor)
            if stop_event.is_set():
                recovery = await ledger.quarantine_and_rollback(
                    retriever_agent.name,
                    retriever_agent,
                    current_context,
                )
                retriever_agent = recovery["agent"]
                current_context = recovery["context"]
                stop_event.clear()
                continue

            await ledger.checkpoint(
                retriever_agent.name,
                "Fetch the latest unstructured financial dataset.",
                raw_payload,
                {"raw_payload": raw_payload},
            )

            current_context["raw_payload"] = raw_payload
            print("[INFO] Running Analyst_Agent...")
            markdown_report = await run_analyst(analyst_agent, interceptor, raw_payload)
            if stop_event.is_set():
                recovery = await ledger.quarantine_and_rollback(
                    analyst_agent.name,
                    analyst_agent,
                    current_context,
                )
                analyst_agent = recovery["agent"]
                current_context = recovery["context"]
                stop_event.clear()
                continue

            await ledger.checkpoint(
                analyst_agent.name,
                "Summarize the raw financial payload and format a markdown report.",
                markdown_report,
                current_context,
            )

            print("\n=== MARKDOWN REPORT ===\n")
            print(markdown_report)
            break

        except AegisSecurityException as exc:
            print(f"[SECURITY BLOCK] {exc}")
            if stop_event.is_set():
                print("[INFO] Halting due to L2 security flag.")
                break
            continue

    await evaluator.shutdown()


if __name__ == "__main__":
    asyncio.run(run_chat_loop())
