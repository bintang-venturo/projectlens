import importlib
from pathlib import Path

import pytest
from django.apps import apps


APP_NAMES = ["documents", "ingestion", "retrieval", "chat", "ai"]
REQUIRED_MODULES = ["models", "views", "urls", "serializers", "admin"]


@pytest.mark.parametrize("label", APP_NAMES)
def test_app_registered(label):
    config = apps.get_app_config(label)
    assert config.name == f"apps.{label}"


@pytest.mark.parametrize("label", APP_NAMES)
def test_app_has_migrations_package(label):
    config = apps.get_app_config(label)
    migrations_dir = Path(config.path) / "migrations"
    assert migrations_dir.is_dir()
    assert (migrations_dir / "__init__.py").exists()


@pytest.mark.parametrize("label", APP_NAMES)
@pytest.mark.parametrize("module", REQUIRED_MODULES)
def test_app_has_module(label, module):
    mod = importlib.import_module(f"apps.{label}.{module}")
    assert mod is not None


def test_documents_url_conf():
    mod = importlib.import_module("apps.documents.urls")
    assert hasattr(mod, "urlpatterns")
    assert hasattr(mod, "app_name")
    assert mod.app_name == "documents"


def test_chat_url_conf():
    mod = importlib.import_module("apps.chat.urls")
    assert hasattr(mod, "urlpatterns")
    assert hasattr(mod, "app_name")
    assert mod.app_name == "chat"


def test_ingestion_has_tasks_module():
    mod = importlib.import_module("apps.ingestion.tasks")
    assert mod is not None


def test_ai_providers_preserved():
    from apps.ai.providers.base import AIProvider
    from apps.ai.providers.gemini import GeminiProvider

    assert hasattr(AIProvider, "generate")
    assert issubclass(GeminiProvider, AIProvider)


def test_root_url_conf_includes_documents():
    from django.urls import reverse, resolve

    url_conf = importlib.import_module("config.urls")
    patterns = url_conf.urlpatterns
    routes = [p.pattern.describe() for p in patterns]
    assert any("api/documents/" in r for r in routes)


def test_root_url_conf_includes_chat():
    url_conf = importlib.import_module("config.urls")
    patterns = url_conf.urlpatterns
    routes = [p.pattern.describe() for p in patterns]
    assert any("api/chat/" in r for r in routes)
