import io

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from tests.conftest import USER_A, USER_B, as_user


def make_test_pdf(page_texts: list[str]) -> bytes:
    """Build a minimal, real PDF with extractable text on each page."""
    writer = PdfWriter()
    for text in page_texts:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        resources = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        page[NameObject("/Resources")] = resources

        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 11 Tf 50 700 Td ({escaped}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_upload_ingest_reader_and_cited_summary(client, tmp_path, monkeypatch):
    from app.core.config import get_settings

    get_settings().storage_dir = str(tmp_path)

    pid = client.post(
        "/v1/projects",
        json={"name": "Climate", "topic": "Maize yields"},
        headers=as_user(USER_A),
    ).json()["id"]

    pdf_bytes = make_test_pdf(
        [
            (
                "The aim of this study is to examine how seasonal rainfall "
                "variability affects smallholder maize yields in northern Nigeria."
            ),
            (
                "Our methodology used a panel household survey of n = 450 "
                "smallholder maize farmers across three agro-ecological zones."
            ),
            (
                "The results showed a significant 18 percent decrease in maize yield "
                "during late-onset rainfall seasons. A key limitation of this study is "
                "the two-year panel horizon."
            ),
        ]
    )

    r = client.post(
        f"/v1/projects/{pid}/sources/upload",
        files={"file": ("okafor_2021_maize.pdf", pdf_bytes, "application/pdf")},
        headers=as_user(USER_A),
    )
    assert r.status_code == 201, r.text
    source = r.json()
    assert source["source_kind"] == "document"
    assert source["document"]["status"] == "ready"
    assert source["document"]["page_count"] == 3

    # Duplicate upload in the same project is rejected with 409
    dup = client.post(
        f"/v1/projects/{pid}/sources/upload",
        files={"file": ("duplicate.pdf", pdf_bytes, "application/pdf")},
        headers=as_user(USER_A),
    )
    assert dup.status_code == 409

    # Reader endpoint returns all 3 extracted pages
    reader = client.get(
        f"/v1/projects/{pid}/sources/{source['id']}/reader",
        headers=as_user(USER_A),
    ).json()
    assert len(reader["pages"]) == 3
    assert "aim of this study" in reader["pages"][0]["text_content"]

    # Summarize generates page-cited sections
    sum_resp = client.post(
        f"/v1/projects/{pid}/sources/{source['id']}/summarize",
        headers=as_user(USER_A),
    )
    assert sum_resp.status_code == 200, sum_resp.text
    sections = sum_resp.json()["sections"]
    assert sections["aim"]["page_number"] == 1
    assert "examine how seasonal rainfall" in sections["aim"]["text"]
    assert sections["methodology"]["page_number"] == 2
    assert sections["findings"]["page_number"] == 3
    assert sections["limitations"]["page_number"] == 3

    # Download original PDF file
    dl = client.get(
        f"/v1/projects/{pid}/sources/{source['id']}/file",
        headers=as_user(USER_A),
    )
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF-")

    # User B cannot access User A's reader or file
    assert (
        client.get(
            f"/v1/projects/{pid}/sources/{source['id']}/reader",
            headers=as_user(USER_B),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/v1/projects/{pid}/sources/{source['id']}/file",
            headers=as_user(USER_B),
        ).status_code
        == 404
    )


def test_rejects_invalid_and_scanned_pdfs(client, tmp_path):
    from app.core.config import get_settings

    get_settings().storage_dir = str(tmp_path)
    pid = client.post(
        "/v1/projects", json={"name": "P", "topic": "T"}, headers=as_user(USER_A)
    ).json()["id"]

    # Non-PDF bytes rejected with 400
    bad = client.post(
        f"/v1/projects/{pid}/sources/upload",
        files={"file": ("notes.pdf", b"not a pdf", "application/pdf")},
        headers=as_user(USER_A),
    )
    assert bad.status_code == 400

    # Blank/scanned PDF marks document status as 'failed' with clear explanation
    blank_pdf = make_test_pdf([""])
    scanned = client.post(
        f"/v1/projects/{pid}/sources/upload",
        files={"file": ("scanned.pdf", blank_pdf, "application/pdf")},
        headers=as_user(USER_A),
    )
    assert scanned.status_code == 201
    assert scanned.json()["document"]["status"] == "failed"
    assert "scanned" in scanned.json()["document"]["error_message"].lower()
