import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    # API views are cached; start each test from an empty cache.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def no_github_token(monkeypatch):
    # sync_github switches endpoints when GITHUB_TOKEN is set; a token in the developer's or CI's
    # environment must not change what the tests exercise. Tests that need one set it themselves.
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
