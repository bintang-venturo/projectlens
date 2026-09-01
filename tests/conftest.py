from unittest.mock import patch

import django
import pytest
from django.conf import settings


def pytest_configure():
    settings.DJANGO_SETTINGS_MODULE = "config.settings"


@pytest.fixture(autouse=True)
def _mock_embed_and_store(request):
    if "no_embed_mock" in request.keywords:
        yield
        return
    with patch("apps.ingestion.services.embed_and_store_chunks"):
        yield
