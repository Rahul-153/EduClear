import pytest

from backend.app.services import ratelimit


@pytest.fixture(autouse=True)
def _fresh_rate_limit():
    ratelimit.reset()
    yield
