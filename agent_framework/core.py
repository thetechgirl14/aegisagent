"""
agent_framework.core — Agent base class and tool-calling loop.

Full implementation available under licence — contact: kattrahill@inthenexus.tech
"""


class Agent:
    """
    Base agent class with tool-calling loop.

    Wraps an OpenAIChatClient and iterates the model + tool execution
    cycle until the model returns a final response (no tool calls pending).
    """

    def __init__(self, client, system_prompt: str, tools: list = None):
        raise NotImplementedError(
            "Core implementation is proprietary."
        )

    async def run(self, user_message: str) -> str:
        """Execute the agent loop and return the final response."""
        raise NotImplementedError
