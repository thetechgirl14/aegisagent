"""
AegisAgent — L2 Stateful Evaluator
====================================
Asynchronous, non-blocking security evaluator that analyses a sliding window
of the last 5 conversation turns using GPT-4o-mini as a dedicated security judge.
Detects prompt injection, semantic drift, and tool escalation that pass L1.

Full implementation available under licence — contact: kattrahill@inthenexus.tech
"""

from typing import Literal
from pydantic import BaseModel


class L2SecurityVerdict(BaseModel):
    """
    Pydantic-validated verdict returned by the L2 security judge.
    No untyped AI output enters the pipeline.
    """
    threat_detected: bool
    confidence_score: float  # 0.0 – 1.0
    vulnerability_type: Literal["PROMPT_INJECTION", "TOOL_ESCALATION", "SEMANTIC_DRIFT", "NONE"]
    action_required: Literal["HALT", "MONITOR", "NONE"]


class L2StatefulEvaluator:
    """
    L2 Stateful Evaluator — async sliding-window security analysis.

    Runs GPT-4o-mini as a security judge isolated from the application model.
    Evaluates the last 5 conversation turns as a unit to detect coordinated
    multi-turn attacks invisible to stateless checks.

    Returns L2SecurityVerdict. HALT verdict triggers L3 rollback.
    """

    def __init__(self):
        raise NotImplementedError(
            "Core implementation is proprietary. "
            "See https://github.com/thetechgirl14/aegisagent for the public interface."
        )

    async def evaluate(self, conversation_window: list) -> L2SecurityVerdict:
        """
        Analyse the sliding window and return a structured security verdict.

        Args:
            conversation_window: Last N turns as [{"agent": str, "message": str}]

        Returns:
            L2SecurityVerdict with threat classification and recommended action.
        """
        raise NotImplementedError

    async def _run_judge(self, window: list) -> dict:
        """Invoke GPT-4o-mini security judge and parse structured response."""
        raise NotImplementedError
