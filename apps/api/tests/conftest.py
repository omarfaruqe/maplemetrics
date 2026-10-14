import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clean_cache():
    """Throttle counters live in the cache; start every test with a clean slate."""
    cache.clear()
    yield
    cache.clear()
