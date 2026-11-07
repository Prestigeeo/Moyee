import pytest
from sqlalchemy.orm import Session

from app.modules.billing.service import QuotaExceeded, consume
from tests.conftest import USER_A, as_user


def test_public_plans(client):
    plans = client.get("/v1/plans").json()
    assert [p["id"] for p in plans] == ["free", "pro"]
    assert plans[1]["price_usd_cents_monthly"] == 1000


def test_usage_summary_defaults_to_free(client):
    r = client.get("/v1/me/usage", headers=as_user(USER_A))
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["id"] == "free"
    metrics = {u["metric"]: u for u in body["usage"]}
    assert metrics["assistant_messages"]["limit"] == 20
    assert metrics["active_projects"]["used"] == 0


def test_consume_enforces_daily_limit(client):
    from app.core.db import get_db
    from app.main import app

    client.get("/v1/me", headers=as_user(USER_A))  # creates profile
    db: Session = next(app.dependency_overrides[get_db]())
    for _ in range(20):
        consume(db, USER_A, "assistant_messages")
    with pytest.raises(QuotaExceeded) as exc:
        consume(db, USER_A, "assistant_messages")
    assert exc.value.limit == 20
    assert exc.value.resets_at is not None

    usage = client.get("/v1/me/usage", headers=as_user(USER_A)).json()["usage"]
    assert next(u for u in usage if u["metric"] == "assistant_messages")["used"] == 20


def test_profile_update_and_delete(client):
    r = client.patch(
        "/v1/me",
        json={"full_name": "Ada Okafor", "research_level": "postgraduate"},
        headers=as_user(USER_A),
    )
    assert r.json()["full_name"] == "Ada Okafor"
    client.post("/v1/projects", json={"name": "P", "topic": "T"}, headers=as_user(USER_A))
    assert client.delete("/v1/me", headers=as_user(USER_A)).status_code == 204
    # Profile is recreated empty on next access; projects are gone.
    assert client.get("/v1/me", headers=as_user(USER_A)).json()["full_name"] is None
    assert client.get("/v1/projects", headers=as_user(USER_A)).json() == []
