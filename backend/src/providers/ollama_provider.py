import os
import logging
import requests as http_req
from openai import OpenAI
from .base import BaseProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    def __init__(self):
        base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1/")
        self.client = OpenAI(base_url=base_url, api_key="ollama")
        self._base_url = base_url

    def chat(self, system: str, messages: list[dict], tools: list[dict], model: str) -> tuple[str, list[dict]]:
        openai_messages = [{"role": "system", "content": system}] + [
            {"role": m["role"], "content": m.get("content") or ""}
            for m in messages
            if m["role"] in ("user", "assistant")
        ]

        response = self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
        )
        return response.choices[0].message.content or "", []

    def list_models(self) -> list[str]:
        try:
            ollama_base = self._base_url.rstrip("/").removesuffix("/v1")
            resp = http_req.get(f"{ollama_base}/api/tags", timeout=5)
            if resp.ok:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception as exc:
            logger.debug("Could not fetch Ollama models: %s", exc)
        return []

    def supports_tool_use(self) -> bool:
        return False
