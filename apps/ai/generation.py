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


def get_extraction_provider() -> AIProvider:
    if "extraction" not in _generation_cache:
        provider_name = settings.GENERATION_PROVIDER
        if provider_name == "gemini":
            from apps.ai.providers.gemini import GeminiProvider

            _generation_cache["extraction"] = GeminiProvider(
                max_output_tokens=settings.EXTRACTION_MAX_OUTPUT_TOKENS,
                temperature=settings.EXTRACTION_TEMPERATURE,
                response_mime_type="application/json",
            )
        else:
            raise ValueError(f"Unknown generation provider: {provider_name}")
    return _generation_cache["extraction"]
