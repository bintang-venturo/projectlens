from django.conf import settings

from apps.ai.providers.base import AIProvider

_generation_cache: dict[str, AIProvider] = {}


def get_generation_provider() -> AIProvider:
    provider_name = settings.GENERATION_PROVIDER
    if provider_name not in _generation_cache:
        if provider_name == "gemini":
            from apps.ai.providers.gemini import GeminiProvider

            _generation_cache[provider_name] = GeminiProvider()
        else:
            raise ValueError(f"Unknown generation provider: {provider_name}")
    return _generation_cache[provider_name]
