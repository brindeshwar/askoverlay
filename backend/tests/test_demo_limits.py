"""The demo is the only place the backend's own Gemini key is spent, so its caps are tested hard."""
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import main
from database import connection
from database.models import DailyUsage, Device
from services import quota_service as quota
from agent.errors import ChatError
from services.quota_service import DemoDecision, DemoLimits


def new_device():
    return str(uuid.uuid4())


def chat(client, device_id, ip=None):
    headers = {"X-Device-Id": device_id}
    if ip:
        headers["X-Forwarded-For"] = ip
    return client.post("/chat", json={"message": "hi"}, headers=headers)


def usage(scope, key=""):
    with connection.SessionLocal() as db:
        row = db.execute(select(DailyUsage).where(DailyUsage.scope == scope, DailyUsage.key == key)).scalar_one_or_none()
        return row.request_count if row else 0


def device_usage(device_id):
    with connection.SessionLocal() as db:
        row = db.get(Device, device_id)
        return row.request_count if row else 0


# --- the forgery problem: device ids are free to mint -------------------------------------------

def test_cycling_fresh_device_ids_from_one_ip_hits_the_ip_cap(client, settings_override, fake_gemini):
    settings_override(demo_ip_daily_limit=5, trust_forwarded_for=True)
    codes = [chat(client, new_device(), ip="203.0.113.7").status_code for _ in range(8)]
    assert codes == [200] * 5 + [429] * 3  # a new uuid per request buys nothing past the IP cap
    assert len(fake_gemini.calls) == 5


def test_different_ips_have_independent_ip_caps(client, settings_override, fake_gemini):
    settings_override(demo_ip_daily_limit=1, trust_forwarded_for=True)
    assert chat(client, new_device(), ip="198.51.100.1").status_code == 200
    assert chat(client, new_device(), ip="198.51.100.2").status_code == 200
    assert chat(client, new_device(), ip="198.51.100.1").status_code == 429


def test_global_cap_stops_a_distributed_attacker_and_says_so(client, settings_override, fake_gemini):
    settings_override(demo_global_daily_limit=4, trust_forwarded_for=True)
    codes = [chat(client, new_device(), ip=f"192.0.2.{i}").status_code for i in range(7)]
    assert codes == [200] * 4 + [503] * 3
    assert "daily capacity" in chat(client, new_device(), ip="192.0.2.99").json()["detail"]
    assert len(fake_gemini.calls) == 4  # spend is bounded no matter how many ips or devices


def test_ip_cap_message_is_distinct_from_the_device_cap_message(client, settings_override, fake_gemini):
    settings_override(demo_ip_daily_limit=1, trust_forwarded_for=True)
    chat(client, new_device(), ip="203.0.113.5")
    assert "network" in chat(client, new_device(), ip="203.0.113.5").json()["detail"]


def test_device_cap_is_reported_before_the_capacity_messages(client, settings_override, fake_gemini):
    settings_override(demo_request_limit=1, demo_global_daily_limit=1, trust_forwarded_for=True)
    device = new_device()
    assert chat(client, device, ip="203.0.113.9").status_code == 200  # uses the only global slot too
    assert "Demo limit reached" in chat(client, device, ip="203.0.113.9").json()["detail"]


# --- all or nothing -----------------------------------------------------------------------------

def test_rejected_request_consumes_nothing_anywhere(client, fake_gemini):
    limits = DemoLimits(device_lifetime=10, ip_daily=1, global_daily=100)
    assert quota.consume_demo_request("dev-aaaaaaaa", "10.0.0.1", limits) is DemoDecision.ALLOWED
    # Second device, same ip: IP cap rejects it - its own counter and the global one must roll back.
    assert quota.consume_demo_request("dev-bbbbbbbb", "10.0.0.1", limits) is DemoDecision.IP_LIMIT
    assert device_usage("dev-bbbbbbbb") == 0
    assert usage("global") == 1
    assert usage("ip", "10.0.0.1") == 1


def test_device_cap_rejection_does_not_burn_ip_or_global_budget(client, fake_gemini):
    limits = DemoLimits(device_lifetime=1, ip_daily=100, global_daily=100)
    quota.consume_demo_request("dev-cccccccc", "10.0.0.2", limits)
    for _ in range(5):
        assert quota.consume_demo_request("dev-cccccccc", "10.0.0.2", limits) is DemoDecision.DEVICE_LIMIT
    assert usage("ip", "10.0.0.2") == 1
    assert usage("global") == 1


def test_caps_hold_under_concurrency(client, settings_override, fake_gemini):
    settings_override(demo_request_limit=100, demo_ip_daily_limit=6, trust_forwarded_for=True)

    def hit(_):
        return TestClient(main.app).post(
            "/chat", json={"message": "x"}, headers={"X-Device-Id": new_device(), "X-Forwarded-For": "203.0.113.50"}
        ).status_code

    with ThreadPoolExecutor(12) as pool:
        codes = list(pool.map(hit, range(40)))
    assert codes.count(200) == 6
    assert usage("ip", "203.0.113.50") == 6
    assert usage("global") == 6


# --- fairness: don't charge users for our failures ------------------------------------------------

def test_upfront_gemini_failure_refunds_every_counter(client, settings_override, fake_gemini):
    settings_override(trust_forwarded_for=True)
    fake_gemini.error = ChatError(503, "Gemini is rate-limiting requests right now. Try again in a moment.")
    device = new_device()
    assert chat(client, device, ip="203.0.113.60").status_code == 503
    assert device_usage(device) == 0
    assert usage("ip", "203.0.113.60") == 0
    assert usage("global") == 0


def test_successful_request_is_not_refunded(client, settings_override, fake_gemini):
    settings_override(trust_forwarded_for=True)
    device = new_device()
    chat(client, device, ip="203.0.113.61")
    assert device_usage(device) == 1
    assert usage("ip", "203.0.113.61") == 1


def test_byok_never_touches_any_demo_counter(client, fake_gemini):
    for _ in range(5):
        client.post("/chat", json={"message": "hi"}, headers={"X-Gemini-Key": "k"})
    assert usage("global") == 0


# --- which ip do we believe? ---------------------------------------------------------------------

def test_forwarded_for_is_ignored_unless_trusted(client, settings_override, fake_gemini):
    settings_override(demo_ip_daily_limit=2)  # trust_forwarded_for defaults to False
    codes = [chat(client, new_device(), ip=f"203.0.113.{i}").status_code for i in range(4)]
    assert codes == [200, 200, 429, 429]  # spoofed headers can't dodge the cap; all count as the socket peer


def test_only_the_last_forwarded_entry_is_trusted(client, settings_override, fake_gemini):
    settings_override(demo_ip_daily_limit=1, trust_forwarded_for=True)
    # The client-supplied prefix is attacker-controlled; the last hop is what our proxy appended.
    assert chat(client, new_device(), ip="1.1.1.1, 203.0.113.70").status_code == 200
    assert chat(client, new_device(), ip="2.2.2.2, 203.0.113.70").status_code == 429


@pytest.mark.parametrize("limit_name", ["demo_request_limit", "demo_ip_daily_limit", "demo_global_daily_limit"])
def test_limits_must_be_positive(limit_name):
    from config import Settings

    with pytest.raises(ValueError):
        Settings(_env_file=None, **{limit_name: 0})
