"""
agent_framework — lightweight shim over the Azure OpenAI SDK.

Provides the Agent and Message primitives used throughout AegisAgent so the
pipeline is self-contained and can be run directly without any third-party
agent orchestration dependency.
"""

from .core import Agent, Message

__all__ = ["Agent", "Message"]
