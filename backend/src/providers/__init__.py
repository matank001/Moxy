from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider

_PROVIDERS = {
    'anthropic': AnthropicProvider,
    'openai': OpenAIProvider,
    'ollama': OllamaProvider,
}


def get_provider(name: str):
    """Return an instantiated provider by name. Raises ValueError for unknown names."""
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider: {name}. Choose from: {list(_PROVIDERS)}")
    return cls()
