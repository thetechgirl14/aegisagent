"""
OpenAIChatClient — thin async wrapper around the Azure OpenAI SDK.

Used by Agent for chat completions and by L2_Stateful_Evaluator for
security analysis of sliding-window conversation turns.
"""

from __future__ import annotations

from typing import Any, List, TYPE_CHECKING

try:
    from openai import AsyncAzureOpenAI
except ImportError:  # pragma: no cover — openai not installed in test sandbox
    AsyncAzureOpenAI = None  # type: ignore[assignment,misc]

if TYPE_CHECKING:
    from .core import Message


class _ResponseMessage:
    """Wraps a completion message so callers can access `.text`."""

    def __init__(self, content: str) -> None:
        self.text = content


class _Response:
    """Wraps a raw OpenAI completion into the shape expected by L2_Stateful_Evaluator."""

    def __init__(self, content: str) -> None:
        self.messages: List[_ResponseMessage] = [_ResponseMessage(content)]


class OpenAIChatClient:
    """Async client for Azure OpenAI chat completions.

    Parameters
    ----------
    azure_endpoint:
        Full Azure OpenAI endpoint URL, e.g. ``https://<resource>.openai.azure.com``.
    api_key:
        Azure OpenAI API key.
    model:
        Deployment name / model ID (e.g. ``gpt-4o-mini``).
    api_version:
        Azure OpenAI REST API version string.
    """

    def __init__(
        self,
        azure_endpoint: str,
        api_key: str,
        model: str,
        api_version: str = "2024-12-01-preview",
    ) -> None:
        if AsyncAzureOpenAI is None:
            raise ImportError(
                "The 'openai' package is required to use OpenAIChatClient. "
                "Install it with: pip install openai"
            )
        self.model = model
        self._client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    async def chat_complete(self, messages: List[dict], **kwargs: Any):
        """Low-level pass-through to the Azure OpenAI chat completions API.

        Returns the raw OpenAI response object so ``Agent`` can inspect
        ``choices[0].message`` and ``tool_calls`` directly.
        """
        return await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )

    async def get_response(self, messages: "List[Message]") -> _Response:
        """Higher-level helper used by L2_Stateful_Evaluator.

        Accepts a list of ``Message`` objects and returns a ``_Response``
        whose ``.messages[0].text`` holds the raw completion string.
        """
        raw_messages = [m.to_dict() for m in messages]
        completion = await self._client.chat.completions.create(
            model=self.model,
            messages=raw_messages,
        )
        content = completion.choices[0].message.content or ""
        return _Response(content)
