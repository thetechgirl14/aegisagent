"""
agent_framework — Neumann Nexus Azure OpenAI Agent SDK
=======================================================
Lightweight, self-owned agent SDK wrapping Azure OpenAI.
No third-party agent framework dependency.

Full implementation available under licence — contact: kattrahill@inthenexus.tech
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Message:
    """A single conversation message."""
    role: str   # "system" | "user" | "assistant"
    content: List[str]

    @property
    def text(self) -> str:
        return " ".join(self.content) if self.content else ""
