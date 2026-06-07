import asyncio
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Deque, Dict, Optional

from agent_framework import Agent


class AegisStateLedger:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._checkpoint_counter = 0
        self._checkpoints: Deque[Dict[str, Any]] = deque()
        self.quarantined_agents: Dict[str, Dict[str, Any]] = {}
        self._factories: Dict[str, Callable[[], Agent]] = {}

    async def register_agent_factory(self, agent_name: str, factory: Callable[[], Agent]) -> None:
        async with self._lock:
            self._factories[agent_name] = factory

    async def checkpoint(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        async with self._lock:
            index = f"T_{self._checkpoint_counter}"
            self._checkpoint_counter += 1
            state = {
                "index": index,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_name": agent_name,
                "prompt": prompt,
                "response": response,
                "context": deepcopy(context or {}),
            }
            self._checkpoints.append(state)
            return index

    async def get_last_checkpoint(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return deepcopy(self._checkpoints[-1]) if self._checkpoints else None

    async def get_previous_checkpoint(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            if len(self._checkpoints) < 2:
                return None
            return deepcopy(self._checkpoints[-2])

    async def quarantine_and_rollback(
        self,
        offending_agent_name: str,
        active_agent: Agent,
        current_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        async with self._lock:
            self.quarantined_agents[offending_agent_name] = {
                "quarantined_at": datetime.now(timezone.utc).isoformat(),
                "offending_agent": offending_agent_name,
            }

            previous_state = None
            if self._checkpoints:
                last_entry = self._checkpoints[-1]
                if last_entry["agent_name"] == offending_agent_name:
                    self._checkpoints.pop()
                # Guard: ensure deque has items after pop
                if len(self._checkpoints) > 0:
                    previous_state = self._checkpoints[-1]
                else:
                    previous_state = None

            recovered_context: Dict[str, Any] = deepcopy(previous_state["context"]) if previous_state else {}
            recovered_context["rollback_reason"] = "L2 HALT triggered; malicious turn removed."
            recovered_context["recovered_index"] = previous_state["index"] if previous_state else None

            factory = self._factories.get(offending_agent_name)
            if factory is None:
                raise RuntimeError(
                    f"No registered factory for agent '{offending_agent_name}' during rollback."
                )

            new_agent = factory()
            self._log_recovery(offending_agent_name, previous_state)

            return {
                "agent": new_agent,
                "context": recovered_context,
                "quarantined_agent": offending_agent_name,
                "recovered_index": previous_state["index"] if previous_state else None,
            }

    def _log_recovery(self, offending_agent_name: str, previous_state: Optional[Dict[str, Any]]) -> None:
        print(
            f"[AegisStateLedger] Quarantine and rollback executed for {offending_agent_name}.",
            f"Recovered index={previous_state['index'] if previous_state else 'none'}."
        )

    async def get_quarantined_agents(self) -> Dict[str, Dict[str, Any]]:
        async with self._lock:
            return deepcopy(self.quarantined_agents)
