import base64
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

import main
from agent.errors import ChatError
from agent.screenshot import MAX_SCREENSHOT_BYTES


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


def test_demo_uses_the_backend_key(client, fake_gemini):
    post(client, device())
    assert fake_gemini.calls[0]["api_key"] == "backend-key"


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


def test_history_is_forwarded_as_role_text_pairs(client, fake_gemini):
    turns = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    post(client, {"X-Gemini-Key": "k"}, history=turns, message="and now?")
    call = fake_gemini.calls[0]
    assert call["history"] == [("user", "hi"), ("assistant", "hello")]
    assert call["message"] == "and now?"


def test_a_long_past_assistant_reply_is_accepted_in_history(client, fake_gemini):
    long_reply = [{"role": "assistant", "content": "y" * 20_000}]  # replies can exceed the 8000-char message limit
    assert post(client, {"X-Gemini-Key": "k"}, history=long_reply).status_code == 200


def test_history_is_optional(client, fake_gemini):
    assert post(client, {"X-Gemini-Key": "k"}).status_code == 200
    assert fake_gemini.calls[0]["history"] == []


def test_stream_response_is_sse(client, fake_gemini):
    r = post(client, {"X-Gemini-Key": "k"})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.text.endswith("data: [DONE]\n\n")


def test_upfront_gemini_failure_becomes_a_real_status(client, fake_gemini):
    fake_gemini.error = ChatError(503, "Gemini is rate-limiting requests right now. Try again in a moment.")
    r = post(client, {"X-Gemini-Key": "k"})
    assert r.status_code == 503
    assert "rate-limiting" in r.json()["detail"]


def test_input_validation(client, fake_gemini):
    byok = {"X-Gemini-Key": "k"}
    assert post(client, byok, message="").status_code == 422
    assert post(client, byok, message="   ").status_code == 422
    assert post(client, byok, message="x" * 8001).status_code == 422
    assert post(client, byok, history=[{"role": "system", "content": "x"}]).status_code == 422  # only user/assistant
    assert post(client, byok, history=[{"role": "user", "content": "x"}] * 41).status_code == 422  # too many turns
    big = [{"role": "user", "content": "x" * 8000}] * 8  # each is fine, together they exceed the request budget
    assert post(client, byok, history=big).status_code == 422
    assert post(client, byok, history=[{"role": "user", "content": "x" * 60_001}]).status_code == 422
    assert post(client, {"X-Device-Id": "short"}).status_code == 422
    assert post(client, {"X-Device-Id": "d" * 65}).status_code == 422
    assert fake_gemini.calls == []


# ── screenshots ───────────────────────────────────────────────────────────────

def png_b64(extra: bytes = b"") -> str:
    return base64.b64encode(b"\x89PNG\r\n\x1a\n" + extra).decode()


def test_a_screenshot_is_passed_to_the_agent(client, fake_gemini):
    shot = png_b64(b"pixels")
    assert post(client, {"X-Gemini-Key": "k"}, screenshot=shot).status_code == 200
    passed = fake_gemini.calls[0]["screenshot"]
    assert passed.mime == "image/png" and passed.data == shot


def test_no_screenshot_means_none(client, fake_gemini):
    post(client, {"X-Gemini-Key": "k"})
    assert fake_gemini.calls[0]["screenshot"] is None


def test_a_bad_screenshot_is_rejected_and_not_echoed(client, fake_gemini):
    marker = "NOT-AN-IMAGE-" + "A" * 200
    response = post(client, {"X-Gemini-Key": "k"}, screenshot=marker)
    assert response.status_code == 422
    assert marker not in response.text
    assert fake_gemini.calls == []


def test_an_oversized_screenshot_is_rejected_and_not_echoed(client, fake_gemini):
    huge = png_b64(b"x" * (MAX_SCREENSHOT_BYTES + 1000))
    response = post(client, {"X-Gemini-Key": "k"}, screenshot=huge)
    assert response.status_code == 422
    assert huge[:100] not in response.text
    assert fake_gemini.calls == []


def test_a_demo_request_with_a_screenshot_counts_as_one(client, fake_gemini):
    headers = device()
    assert post(client, headers, screenshot=png_b64(b"x")).status_code == 200
    assert client.get("/quota/status", headers=headers).json()["used"] == 1


def test_a_rejected_screenshot_does_not_cost_a_demo_request(client, fake_gemini):
    headers = device()
    assert post(client, headers, screenshot="garbage!").status_code == 422
    assert client.get("/quota/status", headers=headers).json()["used"] == 0
