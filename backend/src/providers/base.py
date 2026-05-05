from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract AI provider. All providers use OpenAI-compatible message format as the
    normalized interchange format. Each provider converts internally as needed."""

    @abstractmethod
    def chat(self, system: str, messages: list[dict], tools: list[dict], model: str) -> tuple[str, list[dict]]:
        """Send a chat request.

        Args:
            system: System prompt string.
            messages: Conversation history in OpenAI format:
                - {"role": "user", "content": str}
                - {"role": "assistant", "content": str, "tool_calls": [...]}
                - {"role": "tool", "tool_call_id": str, "content": str}
            tools: Tool definitions in OpenAI function-calling format:
                [{"type": "function", "function": {"name": str, "description": str, "parameters": {...}}}]
            model: Model ID string.

        Returns:
            (response_text, tool_calls) where tool_calls is a list of:
                {"id": str, "name": str, "input": dict}
        """

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return available model ID strings for the frontend selector."""

    @abstractmethod
    def supports_tool_use(self) -> bool:
        """Whether this provider supports structured tool calling."""
