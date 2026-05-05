import json
import os
import anthropic
from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    MODELS = ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def chat(self, system: str, messages: list[dict], tools: list[dict], model: str) -> tuple[str, list[dict]]:
        anthropic_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            }
            for t in tools
        ]

        anthropic_messages = self._convert_messages(messages)

        kwargs = {
            "model": model,
            "max_tokens": 8096,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": anthropic_messages,
        }
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = self.client.messages.create(**kwargs)

        text = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})

        return text, tool_calls

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI-format messages to Anthropic format."""
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg["role"]

            if role == "user":
                result.append({"role": "user", "content": msg["content"]})
                i += 1

            elif role == "assistant":
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg.get("tool_calls", []):
                    args = tc["function"]["arguments"]
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(args) if isinstance(args, str) else args,
                    })
                if not content:
                    content = [{"type": "text", "text": ""}]
                result.append({"role": "assistant", "content": content})
                i += 1

            elif role == "tool":
                # Collect consecutive tool results into one user message
                tool_results = []
                while i < len(messages) and messages[i]["role"] == "tool":
                    tm = messages[i]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tm["tool_call_id"],
                        "content": tm["content"],
                    })
                    i += 1
                result.append({"role": "user", "content": tool_results})

            else:
                i += 1

        return result

    def list_models(self) -> list[str]:
        return self.MODELS

    def supports_tool_use(self) -> bool:
        return True
