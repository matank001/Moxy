import json
import os
from openai import OpenAI
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self):
        self.client = OpenAI()

    def chat(self, system: str, messages: list[dict], tools: list[dict], model: str) -> tuple[str, list[dict]]:
        openai_messages = [{"role": "system", "content": system}] + messages

        kwargs = {
            "model": model,
            "messages": openai_messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        text = msg.content or ""
        tool_calls = []

        for tc in (msg.tool_calls or []):
            tool_calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "input": json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments,
            })

        return text, tool_calls

    def list_models(self) -> list[str]:
        try:
            models = self.client.models.list()
            return sorted([m.id for m in models.data if "gpt" in m.id])
        except Exception:
            return ["gpt-4o", "gpt-4o-mini"]

    def supports_tool_use(self) -> bool:
        return True
