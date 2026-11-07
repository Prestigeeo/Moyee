import hashlib
import hmac
import io
import json

from docx import Document as DocxDocument

from app.core.config import get_settings
from tests.conftest import USER_A, USER_B, as_user


def test_writing_studio_citations_assist_and_docx_export(client):
    pid = client.post(
        "/v1/projects",
        json={
            "name": "Climate & Maize",
            "topic": "Effects of rainfall variability on maize yield",
            "template": "thesis",
            "citation_style": "apa7",
        },
        headers=as_user(USER_A),
    ).json()["id"]

    src = client.post(
        f"/v1/projects/{pid}/sources",
        json={
            "title": "Seasonal rainfall and maize yields",
            "authors": [{"name": "Ada Okafor", "given": "Ada", "family": "Okafor"}],
            "publication_year": 2021,
            "venue": "Agricultural Systems",
        },
        headers=as_user(USER_A),
    ).json()

    # 1. Fetching the writing studio auto-initialises the 6 Thesis chapters
    doc = client.get(f"/v1/projects/{pid}/writing", headers=as_user(USER_A)).json()
    assert len(doc["sections"]) == 6
    assert doc["sections"][1]["title"] == "Chapter One: Introduction"

    # 2. Edit section content and cite the source
    sections = doc["sections"]
    sections[1]["content"] = (
        "Rainfall variability significantly reduces smallholder maize yields (Okafor, 2021)."
    )
    updated = client.patch(
        f"/v1/projects/{pid}/writing/{doc['id']}",
        json={"sections": sections, "cited_source_ids": [src["id"]]},
        headers=as_user(USER_A),
    ).json()
    assert updated["word_count"] == 9
    assert any("Okafor, A. (2021)." in ref for ref in updated["bibliography"])

    # 3. Responsible AI writing assist returns suggestion diff without inventing sources
    assist = client.post(
        f"/v1/projects/{pid}/writing/assist",
        json={
            "action": "academic_tone",
            "text": "The data shows a lot of farmers don't get enough rain.",
        },
        headers=as_user(USER_A),
    ).json()
    assert "substantial" in assist["suggestion"]
    assert "do not" in assist["suggestion"]

    # 4. Export DOCX and verify headings, paragraph content, and References section
    docx_resp = client.get(
        f"/v1/projects/{pid}/writing/{doc['id']}/docx",
        headers=as_user(USER_A),
    )
    assert docx_resp.status_code == 200
    parsed = DocxDocument(io.BytesIO(docx_resp.content))
    full_docx_text = "\n".join(p.text for p in parsed.paragraphs)
    assert "Chapter One: Introduction" in full_docx_text
    assert "(Okafor, 2021)" in full_docx_text
    assert "References" in full_docx_text
    assert "Okafor, A. (2021)." in full_docx_text

    # 5. User B cannot access User A's writing document or export
    assert client.get(f"/v1/projects/{pid}/writing", headers=as_user(USER_B)).status_code == 404
    assert (
        client.get(
            f"/v1/projects/{pid}/writing/{doc['id']}/docx", headers=as_user(USER_B)
        ).status_code
        == 404
    )


def test_paystack_webhook_signature_and_pro_upgrade(client):
    client.get("/v1/me", headers=as_user(USER_A))

    # Reject invalid webhook signature
    bad = client.post(
        "/v1/billing/webhooks/paystack",
        content=b"{}",
        headers={"X-Paystack-Signature": "invalid"},
    )
    assert bad.status_code == 401

    # Valid signed webhook upgrades User A to Pro
    payload = json.dumps(
        {
            "event": "charge.success",
            "data": {"reference": "ref_pro_123", "metadata": {"user_id": str(USER_A)}},
        }
    ).encode("utf-8")
    sig = hmac.new(
        get_settings().paystack_secret_key.encode("utf-8"), payload, hashlib.sha512
    ).hexdigest()
    ok = client.post(
        "/v1/billing/webhooks/paystack",
        content=payload,
        headers={"X-Paystack-Signature": sig},
    )
    assert ok.status_code == 200

    usage = client.get("/v1/me/usage", headers=as_user(USER_A)).json()
    assert usage["plan"]["id"] == "pro"

    # Cancel reverts to free plan
    cancelled = client.post("/v1/billing/cancel", headers=as_user(USER_A)).json()
    assert cancelled["plan"]["id"] == "free"
