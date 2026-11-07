from tests.conftest import USER_A, USER_B, as_user
from tests.test_ingestion_and_reader import make_test_pdf


def test_literature_matrix_extraction_editing_csv_and_quota(client, tmp_path):
    from app.core.config import get_settings

    get_settings().storage_dir = str(tmp_path)

    pid = client.post(
        "/v1/projects",
        json={"name": "Climate", "topic": "Rainfall variability and maize yield"},
        headers=as_user(USER_A),
    ).json()["id"]

    pdf_a = make_test_pdf(
        [
            (
                "The aim of this study is to examine how seasonal rainfall variability "
                "affects smallholder maize yield in northern Nigeria."
            ),
            (
                "Our methodology used a quantitative panel household survey of n = 450 "
                "smallholder households analysed with fixed-effects regression."
            ),
            (
                "The results showed an 18 percent decrease in maize yield during late "
                "rainfall onset. A limitation of this study is the two-year horizon."
            ),
        ]
    )
    src_a = client.post(
        f"/v1/projects/{pid}/sources/upload",
        files={"file": ("okafor_2021.pdf", pdf_a, "application/pdf")},
        headers=as_user(USER_A),
    ).json()

    src_b = client.post(
        f"/v1/projects/{pid}/sources",
        json={
            "title": "Satellite rainfall estimates and crop adaptation in Ghana",
            "authors": [{"name": "Kofi Mensah", "given": "Kofi", "family": "Mensah"}],
            "publication_year": 2023,
            "abstract": (
                "The purpose of this paper is to investigate satellite rainfall records. "
                "The results showed significant adaptation through drought-tolerant seeds."
            ),
        },
        headers=as_user(USER_A),
    ).json()

    # Create a comparative literature matrix across both sources
    r = client.post(
        f"/v1/projects/{pid}/matrices",
        json={
            "name": "West Africa Maize Synthesis",
            "source_ids": [src_a["id"], src_b["id"]],
        },
        headers=as_user(USER_A),
    )
    assert r.status_code == 201, r.text
    matrix = r.json()
    assert len(matrix["entries"]) == 2

    row_a = next(e for e in matrix["entries"] if e["project_source_id"] == src_a["id"])
    assert row_a["cells"]["aim"]["page_number"] == 1
    assert row_a["cells"]["methodology"]["page_number"] == 2
    assert row_a["cells"]["findings"]["page_number"] == 3
    assert row_a["cells"]["limitations"]["page_number"] == 3

    row_b = next(e for e in matrix["entries"] if e["project_source_id"] == src_b["id"])
    # Limitations were not in src_b's abstract -> marked "Not reported", never fabricated
    assert row_b["cells"]["limitations"]["value"] == "Not reported"
    assert row_b["cells"]["limitations"]["page_number"] is None

    # Synthesis notes include themes and human-verification labelled potential gaps
    assert len(matrix["synthesis_notes"]["potential_gaps"]) >= 1
    assert "requires human verification" in matrix["synthesis_notes"]["potential_gaps"][0]

    # Edit a cell inline -> marks user_edited = True and drops stale page citation
    edited = client.patch(
        f"/v1/projects/{pid}/matrices/{matrix['id']}/entries/{row_a['id']}",
        json={"field": "aim", "value": "User-refined aim statement."},
        headers=as_user(USER_A),
    ).json()
    edited_row_a = next(e for e in edited["entries"] if e["id"] == row_a["id"])
    assert edited_row_a["cells"]["aim"]["value"] == "User-refined aim statement."
    assert edited_row_a["cells"]["aim"]["user_edited"] is True
    assert edited_row_a["cells"]["aim"]["page_number"] is None

    # Export CSV
    csv_resp = client.get(
        f"/v1/projects/{pid}/matrices/{matrix['id']}/csv",
        headers=as_user(USER_A),
    )
    assert csv_resp.status_code == 200
    assert "Author & Year,Study Title,Research Aim" in csv_resp.text
    assert "User-refined aim statement." in csv_resp.text

    # Free plan allows 1 matrix per project -> creating a second returns 402
    second = client.post(
        f"/v1/projects/{pid}/matrices",
        json={"name": "Second Matrix", "source_ids": [src_a["id"]]},
        headers=as_user(USER_A),
    )
    assert second.status_code == 402
    assert second.json()["metric"] == "matrices_per_project"

    # Cross-user isolation: User B gets 404
    assert (
        client.get(
            f"/v1/projects/{pid}/matrices/{matrix['id']}", headers=as_user(USER_B)
        ).status_code
        == 404
    )
