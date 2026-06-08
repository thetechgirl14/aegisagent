"""
agent_framework.openai — AsyncAzureOpenAI chat client wrapper.

Full implementation available under licence — contact: kattrahill@inthenexus.tech
"""


class OpenAIChatClient:
    """
    Thin async wrapper around Azure OpenAI chat completions.

    Args:
        azure_endpoint: Azure OpenAI resource endpoint URL.
        api_key:        Azure OpenAI API key.
        model:          Deployment name (e.g. 'gpt-4o-mini').
        api_version:    API version string (e.g. '2024-12-01-preview').
    """

    def __init__(self, azure_endpoint: str, api_key: str,
                 model: str, api_version: str):
        raise NotImplementedError(
            "Core implementation is proprietary."
        )

    async def get_response(self, messages: list) -> object:
        """
        Send messages to Azure OpenAI and return the response.

        Args:
            messages: List of Message objects (system + conversation history).

        Returns:
            Response object with .messages[0].text attribute.
        """
        raise NotImplementedError
