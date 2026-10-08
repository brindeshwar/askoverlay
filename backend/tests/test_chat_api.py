import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

import main
from services.gemini_service import GeminiError


def device():
    return {"X-Device-Id": str(uuid.uuid4())}


def post(client, headers=None, **body):
    return client.post("/chat", json={"message": "hi", **body}, headers=headers or {})


def test_health_ok(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_credentials_is_400(client, fake_gemini):
    assert post(client).status_code == 400
    assert fake_gemini.calls == []


def test_quota_status_modes(client):
    assert client.get("/quota/status").json() == {"mode": "byok", "used": None, "limit": None}
    assert client.get("/quota/status", headers=device()).json() == {"mode": "demo", "used": 0, "limit": 3}


def test_demo_is_capped_for_the_lifetime_of_the_device(client, fake_gemini):
    headers = device()
    codes = [post(client, headers).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    assert len(fake_gemini.calls) == 3  # rejected requests never reach Gemini
    assert client.get("/quota/status", headers=headers).json()["used"] == 3
    assert "Demo limit reached (3 requests)" in post(client, headers).json()["detail"]


def test_demo_cap_holds_under_concurrency(client, fake_gemini):
    headers = device()

    def hit(_):
        return TestClient(main.app).post("/chat", json={"message": "x"}, headers=headers).status_code

    with ThreadPoolExecutor(10) as pool:
        codes = list(pool.map(hit, range(30)))
    assert codes.count(200) == 3
    assert codes.count(429) == 27


def test_demo_uses_backend_key_and_configured_model(client, fake_gemini):
    post(client, device())
    call = fake_gemini.calls[0]
    assert call["api_key"] == "backend-key"
    assert call["model"] == "gemini-3.5-flash-lite"
    assert call["timeout"] == 60


def test_demo_without_backend_key_is_503(client, settings_override, fake_gemini):
    settings_override(backend_gemini_key=None)
    assert post(client, device()).status_code == 503
    assert fake_gemini.calls == []


def test_byok_uses_users_key_and_skips_quota(client, settings_override, fake_gemini):
    settings_override(backend_gemini_key=None)  # BYOK must work even with no backend key
    headers = {"X-Gemini-Key": "user-key"}
    assert [post(client, headers).status_code for _ in range(6)] == [200] * 6  # beyond the demo limit
    assert {c["api_key"] for c in fake_gemini.calls} == {"user-key"}


def test_byok_wins_over_device_header_and_leaves_counter_alone(client, fake_gemini):
    headers = {**device(), "X-Gemini-Key": "user-key"}
    post(client, headers)
    assert client.get("/quota/status", headers=headers).json()["used"] == 0


def test_interaction_id_is_forwarded(client, fake_gemini):
    post(client, {"X-Gemini-Key": "k"}, interaction_id="prev-1")
    assert fake_gemini.calls[0]["previous"] == "prev-1"


def test_stream_response_is_sse(client, fake_gemini):
    r = post(client, {"X-Gemini-Key": "k"})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.text.endswith("data: [DONE]\n\n")


def test_upfront_gemini_failure_becomes_a_real_status(client, fake_gemini):
    fake_gemini.error = GeminiError(503, "Gemini is rate-limiting requests right now. Try again in a moment.")
    r = post(client, {"X-Gemini-Key": "k"})
    assert r.status_code == 503
    assert "rate-limiting" in r.json()["detail"]


def test_input_validation(client, fake_gemini):
    byok = {"X-Gemini-Key": "k"}
    assert post(client, byok, message="").status_code == 422
    assert post(client, byok, message="   ").status_code == 422
    assert post(client, byok, message="x" * 8001).status_code == 422
    assert post(client, byok, interaction_id="i" * 257).status_code == 422
    assert post(client, {"X-Device-Id": "short"}).status_code == 422
    assert post(client, {"X-Device-Id": "d" * 65}).status_code == 422
    assert fake_gemini.calls == []
