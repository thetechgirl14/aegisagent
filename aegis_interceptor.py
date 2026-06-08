"""
AegisAgent — L1 Synchronous Gate
=================================
Real-time inline security gate that evaluates every message and tool call
before it reaches the model. Combines deterministic pattern matching with
Azure AI Content Safety (Prompt Shield) for sub-50ms threat detection.

Full implementation available under licence — contact: kattrahill@inthenexus.tech
"""


class AegisSecurityException(Exception):
    """Raised when the L1 gate detects and blocks a security threat."""
    pass


class AegisInterceptor:
    """
    L1 Synchronous Gate — intercepts every agent message inline.

    Checks (in order):
      1. Payload length gate          — O(1), blocks oversized inputs
      2. Compiled regex corpus        — 26 patterns across 5 attack categories
      3. Azure AI Content Safety      — Prompt Shield primary, analyze_text fallback

    Raises AegisSecurityException on detection. Fail-open: if Azure CS
    is unavailable, regex continues to protect.

    Added latency: < 50ms on the synchronous hot path.
    """

    def __init__(self):
        raise NotImplementedError(
            "Core implementation is proprietary. "
            "See https://github.com/thetechgirl14/aegisagent for the public interface."
        )

    async def L1_Synchronous_Gate(self, payload: str) -> None:
        """
        Evaluate payload against all L1 checks.
        Raises AegisSecurityException if a threat is detected.
        """
        raise NotImplementedError

    async def _check_azure_content_safety(self, payload: str) -> None:
        """Azure AI Content Safety — Prompt Shield + analyze_text fallback."""
        raise NotImplementedError
