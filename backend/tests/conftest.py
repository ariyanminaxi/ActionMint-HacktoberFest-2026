import dataclasses

import pytest

from app import config
from app.providers import base


@pytest.fixture
def anyio_backend():
    """Run async tests on asyncio only; trio is not a dependency of this project."""
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """slowapi keeps per-IP counters for the whole process; reset them between tests."""
    from app.main import limiter
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def offline_providers(monkeypatch):
    """Never let the suite reach a real provider: a developer machine may have live keys."""
    monkeypatch.setattr(base, "settings", dataclasses.replace(config.settings, provider_chain=("mock",)))
    base.reset_circuit()
    yield
    base.reset_circuit()
