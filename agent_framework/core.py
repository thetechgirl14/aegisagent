"""
Core Agent and Message types for the agent_framework shim.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any, Callable, List, Optional

from .openai import OpenAIChatClient


class Message:
    """A single chat message with a role and text content.

    The constructor accepts a list of content parts to mirror the interface
    used by multi-modal agent frameworks; for text-only messages the first
    element is used as the content string.
    """

    def __init__(self, role: str, content: List[Any]) -> None:
        self.role = role
        if len(content) == 1:
            self.text: str = str(content[0])
        else:
            self.text = "\n".join(str(c) for c in content)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.text}

    def __repr__(self) -> str:
        preview = self.text[:60].replace("\n", " ")
        return f"Message(role={self.role!r}, text={preview!r})"


class _AgentResponse:
    """Wraps an OpenAI chat completion into the shape expected by callers."""

    def __init__(self, messages: List[Message]) -> None:
        self.messages = messages


def _build_tool_schema(name: str, func: Callable) -> dict:
    """Generate a minimal OpenAI function schema from a callable's name/docstring."""
    doc = inspect.getdoc(func) or f"Call the {name} tool."
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": doc,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }


class Agent:
    """A minimal async agent that uses an OpenAIChatClient for inference.

    Supports zero-argument async tool functions via OpenAI function calling.
    The agent runs a tool-call loop until the model returns a plain message.
    """

    def __init__(
        self,
        client: OpenAIChatClient,
        name: str,
        instructions: str,
        tools: Optional[List[Callable]] = None,
    ) -> None:
        self.client = client
        self.name = name
        self.instructions = instructions
        self._tools: List[Callable] = tools or []
        # Map tool name → callable for dispatch
        self._tool_registry: dict[str, Callable] = {
            getattr(fn, "__name__", f"tool_{i}"): fn
            for i, fn in enumerate(self._tools)
        }

    async def run(self, prompt: str) -> str:
        """Run the agent on *prompt* and return the final text response."""
        messages: List[dict] = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": prompt},
        ]

        tool_schemas = [
            _build_tool_schema(name, fn)
            for name, fn in self._tool_registry.items()
        ]

        max_iterations = 8  # guard against infinite tool loops
        for _ in range(max_iterations):
            kwargs: dict[str, Any] = {}
            if tool_schemas:
                kwargs["tools"] = tool_schemas
                kwargs["tool_choice"] = "auto"

            response = await self.client.chat_complete(messages, **kwargs)
            choice = response.choices[0]
            msg = choice.message

            # Append assistant turn
            messages.append(msg.model_dump())

            # If no tool calls, we have the final answer
            if not getattr(msg, "tool_calls", None):
                return msg.content or ""

            # Execute each requested tool call
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn = self._tool_registry.get(fn_name)
                if fn is None:
                    tool_result = json.dumps({"error": f"Unknown tool: {fn_name}"})
                else:
                    try:
                        result = fn()
                        if asyncio.iscoroutine(result):
                            result = await result
                        tool_result = json.dumps(result, default=str)
                    except Exception as exc:  # noqa: BLE001
                        tool_result = json.dumps({"error": str(exc)})

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    }
                )

        # Fallback: return last assistant content if loop exhausted
        for m in reversed(messages):
            if m.get("role") == "assistant" and m.get("content"):
                return m["content"]
        return ""
