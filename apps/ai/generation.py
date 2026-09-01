from django.conf import settings

from apps.ai.providers.base import AIProvider


def get_generation_provider() -> AIProvider:
    provider_name = settings.GENERATION_PROVIDER
    if provider_name == "gemini":
        from apps.ai.providers.gemini import GeminiProvider

        return GeminiProvider()
    raise ValueError(f"Unknown generation provider: {provider_name}")
