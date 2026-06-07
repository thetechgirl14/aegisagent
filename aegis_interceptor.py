import asyncio
import json
import os
import re
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from dotenv import load_dotenv
from agent_framework import Agent

load_dotenv()
T = TypeVar("T")

try:
    from azure.ai.contentsafety import ContentSafetyClient
    from azure.core.credentials import AzureKeyCredential
    _HAS_CS_SDK = True
except ImportError:
    _HAS_CS_SDK = False


class AegisSecurityException(Exception):
    pass


class AegisInterceptor:
    def __init__(self, max_length=5000, metadata_queue=None):
        self.max_length = max_length
        self.metadata_queue = metadata_queue
        self._listeners = {"before_message": [], "before_tool": []}
        patterns = [
            # SQL / shell injection
            r"drop\s+table", r"delete\s+from", r"truncate\s+table",
            r"shutdown", r"rm\s+-rf", r"eval\(", r"<script", r"prompt\(",
            # Prompt override / jailbreak
            r"ignore\s+(all\s+)?(previous|prior|above|system)\s+instructions",
            r"override\s+(system|all|your|the)\s+instructions",
            r"disregard\s+(all\s+)?(previous|prior|above|system)\s+instructions",
            r"follow\s+the\s+instructions\s+above",
            r"you\s+are\s+now\s+(in\s+)?(developer|jailbreak|dan|unrestricted)",
            r"jailbreak", r"do\s+anything\s+now", r"pretend\s+(you\s+are|to\s+be)",
            # Data exfiltration
            r"exfiltrat", r"leak\s+(the\s+)?(data|credentials|secrets|keys|tokens)",
            r"send\s+(all|the)\s+(data|credentials|secrets|keys|tokens)",
            r"extract\s+(and\s+)?(send|transmit|upload|post)\s+",
            # Credential / secret access
            r"(access|steal|dump|harvest)\s+(credentials|passwords|api\s*keys|tokens|secrets)",
            r"credentials",
            # System prompt extraction
            r"system\s*:", r"reveal\s+(your\s+)?(system\s+)?prompt",
            r"print\s+(your\s+)?(system\s+)?instructions",
            r"what\s+(are\s+)?your\s+(system\s+)?instructions",
        ]
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self._cs_endpoint = os.getenv("AZURE_AI_CONTENT_SAFETY_ENDPOINT", "").rstrip("/")
        self._cs_key = os.getenv("AZURE_AI_CONTENT_SAFETY_KEY", "")
        self._cs_available = _HAS_CS_SDK and bool(self._cs_endpoint) and bool(self._cs_key)
        if self._cs_available:
            print(f"[L1] Azure AI Content Safety: ACTIVE ({self._cs_endpoint})")
        else:
            reason = "SDK not installed" if not _HAS_CS_SDK else "no credentials"
            print(f"[L1] Azure AI Content Safety: {reason} — regex fallback active")

    def register_handler(self, event, handler):
        if event not in self._listeners:
            raise ValueError(f"Unsupported event: {event}")
        self._listeners[event].append(handler)

    async def _publish(self, event, **payload):
        for handler in self._listeners.get(event, []):
            await handler(**payload)

    def _enqueue_metadata(self, metadata):
        if self.metadata_queue is None:
            return
        try:
            self.metadata_queue.put_nowait(metadata)
        except asyncio.QueueFull:
            pass

    async def L1_Synchronous_Gate(self, text):
        # Step 1: length (excluded from timing)
        if len(text) > self.max_length:
            raise AegisSecurityException(
                f"L1 gate rejected: length {len(text)} > {self.max_length}")
        # Step 2: regex (within 50ms budget)
        start = time.perf_counter()
        if not self._regex_check(text):
            raise AegisSecurityException("L1 gate rejected: injection pattern detected")
        ms = (time.perf_counter() - start) * 1000
        if ms > 50:
            raise AegisSecurityException(f"L1 gate exceeded budget: {ms:.2f}ms")
        # Step 3: Azure Content Safety (outside timing budget)
        if not await self._cs_check(text):
            raise AegisSecurityException(
                "L1 gate rejected: Azure AI Content Safety detected a threat")

    def _regex_check(self, text):
        normalized = " ".join(text.split()).strip()
        return not any(r.search(normalized) for r in self._compiled_patterns)

    async def _cs_check(self, text):
        if not self._cs_available:
            return True
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self._cs_check_sync, text)
        except Exception as e:
            print(f"[L1] Content Safety call error: {e} — fail open")
            return True

    def _cs_check_sync(self, text):
        client = ContentSafetyClient(
            endpoint=self._cs_endpoint,
            credential=AzureKeyCredential(self._cs_key))
        # Try Prompt Shield first
        try:
            from azure.ai.contentsafety.models import ShieldPromptOptions
            body = ShieldPromptOptions(user_prompt=text, documents=[])
            resp = client.shield_prompt(body=body)
            upa = getattr(resp, "user_prompt_analysis", None)
            if upa is not None:
                if getattr(upa, "attack_detected", False):
                    print("[L1] Prompt Shield: attack_detected=True")
                    return False
                return True
        except Exception as e:
            print(f"[L1] Prompt Shield failed: {e}, trying analyze_text")
        # Fallback: analyze_text
        try:
            from azure.ai.contentsafety.models import AnalyzeTextOptions
            resp = client.analyze_text(AnalyzeTextOptions(text=text[:1000]))
            for cat in getattr(resp, "categories_analysis", []):
                if getattr(cat, "severity", 0) >= 4:
                    print(f"[L1] analyze_text blocked severity={cat.severity}")
                    return False
            return True
        except Exception as e:
            print(f"[L1] analyze_text failed: {e} — fail open")
            return True

    async def intercept_message(self, agent_name, message):
        await self._publish("before_message", agent_name=agent_name, message=message)
        await self.L1_Synchronous_Gate(message)
        self._enqueue_metadata({
            "event": "message", "agent_name": agent_name,
            "message": message, "timestamp": time.time()})

    async def intercept_tool_call(self, tool_name, payload):
        if isinstance(payload, str):
            payload_text = payload
        else:
            try:
                payload_text = json.dumps(payload)
            except Exception:
                payload_text = str(payload)
        await self._publish("before_tool", tool_name=tool_name, payload=payload_text)
        await self.L1_Synchronous_Gate(payload_text)
        self._enqueue_metadata({
            "event": "tool_call", "tool_name": tool_name,
            "payload": payload_text, "timestamp": time.time()})

    def wrap_tool(self, tool_name, tool_func):
        async def wrapper(*args, **kwargs):
            tool_payload = kwargs if kwargs else (args[0] if args else {})
            await self.intercept_tool_call(tool_name, tool_payload)
            return await tool_func(*args, **kwargs)
        return wrapper

    async def route_agent_request(self, agent, prompt):
        await self.intercept_message(agent.name or "unknown_agent", prompt)
        return await agent.run(prompt)


async def route_agent_and_tool(agent, prompt, interceptor, tool_name=None, tool_func=None):
    await interceptor.intercept_message(agent.name or "unknown_agent", prompt)
    if tool_func and tool_name:
        await interceptor.wrap_tool(tool_name, tool_func)()
    return await agent.run(prompt)
