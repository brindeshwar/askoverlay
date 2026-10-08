import os
import tempfile

# The engine is created at import time from settings, so point it at a throwaway
# database *before* anything from the app is imported. Env vars beat .env.
_tmp = tempfile.mkdtemp(prefix="askoverlay-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

import main
from agent.errors import ChatError
from config import Settings, get_settings
from database import connection
from database.models import DailyUsage, Device
from routes import chat as chat_module


def make_settings(**overrides) -> Settings:
    values = dict(
        backend_gemini_key="backend-key",
        demo_request_limit=3,
        demo_ip_daily_limit=1000,      # high by default so only the tests about these caps hit them
        demo_global_daily_limit=1000,
        database_url=os.environ["DATABASE_URL"],
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings_override():
    """Replace the app's settings for one test: settings_override(backend_gemini_key=None)."""
    def apply(**overrides):
        main.app.dependency_overrides[get_settings] = lambda: make_settings(**overrides)
    apply()
    yield apply
    main.app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def client(settings_override):
    with TestClient(main.app) as c:  # entering the context runs the lifespan (creates tables)
        # Daily counters are shared by every request in a day, so each test starts from zero.
        with connection.SessionLocal() as db:
            db.execute(delete(DailyUsage))
            db.execute(delete(Device))
            db.commit()
        yield c


@pytest.fixture
def fake_gemini(monkeypatch):
    """Replace the LLM call. Records each call; set .error to make it fail up front."""

    class Fake:
        calls: list
        error: ChatError | None = None

    fake = Fake()
    fake.calls = []

    async def fake_start_chat_stream(api_key, history, message, settings):
        fake.calls.append(dict(api_key=api_key, history=history, message=message, model=settings.gemini_model))
        if fake.error:
            raise fake.error

        async def lines():
            yield 'data: "hello"\n\n'
            yield "data: [DONE]\n\n"

        return lines()

    monkeypatch.setattr(chat_module, "start_chat_stream", fake_start_chat_stream)
    return fake
