import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    # API views are cached; start each test from an empty cache.
    cache.clear()
    yield
    cache.clear()
