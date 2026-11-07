from app.modules.discovery import service as discovery_service
from app.modules.discovery.schemas import DiscoverySearchResponse
from tests.conftest import USER_A, USER_B, as_user

SAMPLE_OPENALEX_WORK = {
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/10.1016/j.agsy.2021.103120",
    "display_name": "Rainfall variability and smallholder maize yields in West Africa",
    "publication_year": 2021,
    "type": "article",
    "cited_by_count": 42,
    "open_access": {"is_oa": True, "oa_url": "https://example.org/paper.pdf"},
    "best_oa_location": {"pdf_url": "https://example.org/paper.pdf"},
    "primary_location": {
        "landing_page_url": "https://doi.org/10.1016/j.agsy.2021.103120",
        "source": {
            "display_name": "Agricultural Systems",
            "host_organization_name": "Elsevier",
        },
    },
    "biblio": {"volume": "190", "issue": "2", "first_page": "10", "last_page": "22"},
    "authorships": [
        {"author": {"display_name": "Ada Okafor"}},
        {"author": {"display_name": "Musa Bello"}},
    ],
    "abstract_inverted_index": {
        "Seasonal": [0],
        "rainfall": [1, 5],
        "variability": [2],
        "affects": [3],
        "maize": [4],
    },
    "keywords": [{"display_name": "Rainfall"}, {"display_name": "Maize"}],
}


def test_normalize_openalex_work_and_abstract_reconstruction():
    work = discovery_service.normalize_openalex_work(SAMPLE_OPENALEX_WORK)
    assert work is not None
    assert work.external_id == "W2741809807"
    assert work.doi == "10.1016/j.agsy.2021.103120"
    assert work.abstract == "Seasonal rainfall variability affects maize rainfall"
    assert [a.family for a in work.authors] == ["Okafor", "Bello"]
    assert work.pages == "10-22"
    assert work.is_open_access is True
    assert work.oa_pdf_url == "https://example.org/paper.pdf"


def test_discovery_search_consumes_quota(client, monkeypatch):
    norm = discovery_service.normalize_openalex_work(SAMPLE_OPENALEX_WORK)
    assert norm is not None
    monkeypatch.setattr(
        discovery_service,
        "search_works",
        lambda q, **_: DiscoverySearchResponse(
            query=q, total=1, page=1, per_page=15, results=[norm]
        ),
    )
    r = client.get("/v1/discovery/search?q=maize+rainfall", headers=as_user(USER_A))
    assert r.status_code == 200
    assert r.json()["results"][0]["external_id"] == "W2741809807"

    usage = client.get("/v1/me/usage", headers=as_user(USER_A)).json()["usage"]
    searches = next(u for u in usage if u["metric"] == "academic_searches")
    assert searches["used"] == 1


def test_save_edit_format_and_export_references(client):
    pid = client.post(
        "/v1/projects",
        json={"name": "Climate", "topic": "Maize", "citation_style": "apa7"},
        headers=as_user(USER_A),
    ).json()["id"]

    norm = discovery_service.normalize_openalex_work(SAMPLE_OPENALEX_WORK)
    assert norm is not None

    # Save from discovery
    r = client.post(
        f"/v1/projects/{pid}/sources/from-discovery",
        json=norm.model_dump(),
        headers=as_user(USER_A),
    )
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["inline_citation"] == "(Okafor & Bello, 2021)"
    assert "Okafor, A., & Bello, M. (2021)." in saved["formatted_reference"]
    assert saved["missing_fields"] == []

    # Saving the same work again is idempotent
    r2 = client.post(
        f"/v1/projects/{pid}/sources/from-discovery",
        json=norm.model_dump(),
        headers=as_user(USER_A),
    )
    assert r2.json()["id"] == saved["id"]

    # Project source_count reflects 1 saved source
    proj = client.get(f"/v1/projects/{pid}", headers=as_user(USER_A)).json()
    assert proj["source_count"] == 1

    # Re-render in IEEE and Harvard styles
    ieee_list = client.get(f"/v1/projects/{pid}/sources?style=ieee", headers=as_user(USER_A)).json()
    assert ieee_list[0]["inline_citation"] == "[1]"
    assert ieee_list[0]["formatted_reference"].startswith('[1] A. Okafor, M. Bello, "Rainfall')

    harvard_list = client.get(
        f"/v1/projects/{pid}/sources?style=harvard", headers=as_user(USER_A)
    ).json()
    assert harvard_list[0]["inline_citation"] == "(Okafor and Bello, 2021)"

    # Add a manual reference with missing metadata and check warnings
    manual = client.post(
        f"/v1/projects/{pid}/sources",
        json={"title": "Unpublished Field Report"},
        headers=as_user(USER_A),
    ).json()
    assert "authors" in manual["missing_fields"]
    assert "publication_year" in manual["missing_fields"]

    # Update manual reference
    updated = client.patch(
        f"/v1/projects/{pid}/sources/{manual['id']}",
        json={
            "authors": [{"name": "Chidi Nwosu", "given": "Chidi", "family": "Nwosu"}],
            "publication_year": 2024,
        },
        headers=as_user(USER_A),
    ).json()
    assert updated["inline_citation"] == "(Nwosu, 2024)"
    assert "authors" not in updated["missing_fields"]

    # Export BibTeX
    bib = client.get(f"/v1/projects/{pid}/sources/bibtex", headers=as_user(USER_A))
    assert bib.status_code == 200
    assert "@article{okafor2021rainfall," in bib.text
    assert "doi = {10.1016/j.agsy.2021.103120}" in bib.text

    # User B cannot read or delete User A's sources
    assert client.get(f"/v1/projects/{pid}/sources", headers=as_user(USER_B)).status_code == 404
    assert (
        client.delete(
            f"/v1/projects/{pid}/sources/{saved['id']}", headers=as_user(USER_B)
        ).status_code
        == 404
    )


def test_openalex_full_text_pdf_auto_import_and_manual_import(client, tmp_path, monkeypatch):
    from app.core.config import get_settings
    from app.modules.library import service as library_service
    from tests.test_ingestion_and_reader import make_test_pdf

    monkeypatch.setattr(get_settings(), "storage_dir", str(tmp_path))

    # Verify arXiv landing URL converts to direct PDF URL
    assert (
        discovery_service.normalize_pdf_url("https://arxiv.org/abs/2401.12345v2")
        == "https://arxiv.org/pdf/2401.12345v2.pdf"
    )

    multi_page_pdf = make_test_pdf(
        [
            "Page 1: Introduction to smallholder maize adaptation in West Africa.",
            "Page 2: Methodology using panel regression across 600 rural households.",
            "Page 3: Findings show drought-tolerant seeds increased yield by 24 percent.",
        ]
    )
    monkeypatch.setattr(library_service, "_fetch_pdf_bytes_from_url", lambda url: multi_page_pdf)

    pid = client.post(
        "/v1/projects",
        json={"name": "FullText", "topic": "Maize adaptation"},
        headers=as_user(USER_A),
    ).json()["id"]

    norm = discovery_service.normalize_openalex_work(SAMPLE_OPENALEX_WORK)
    assert norm is not None

    saved = client.post(
        f"/v1/projects/{pid}/sources/from-discovery",
        json=norm.model_dump(),
        headers=as_user(USER_A),
    ).json()

    assert saved["source_kind"] == "document"
    assert saved["document"] is not None
    assert saved["document"]["page_count"] == 3
    assert saved["document"]["status"] == "ready"

    reader = client.get(
        f"/v1/projects/{pid}/sources/{saved['id']}/reader",
        headers=as_user(USER_A),
    ).json()
    assert len(reader["pages"]) == 3
    assert "panel regression" in reader["pages"][1]["text_content"]
