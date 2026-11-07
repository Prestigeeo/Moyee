from tests.conftest import USER_A, USER_B, as_user

NEW_PROJECT = {
    "name": "Climate & Food Security",
    "topic": "Effects of rainfall variability on smallholder maize yields",
    "research_level": "undergraduate",
    "template": "thesis",
    "citation_style": "apa7",
    "keywords": ["climate", " maize ", "climate", ""],
}


def test_requires_auth(client):
    assert client.get("/v1/projects").status_code == 401


def test_create_list_update_project(client):
    r = client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A))
    assert r.status_code == 201, r.text
    project = r.json()
    assert project["keywords"] == ["climate", "maize"]  # cleaned + deduplicated
    assert project["status"] == "active"

    r = client.get("/v1/projects", headers=as_user(USER_A))
    assert [p["id"] for p in r.json()] == [project["id"]]

    r = client.patch(
        f"/v1/projects/{project['id']}",
        json={"research_questions": ["How does rainfall affect yield?"]},
        headers=as_user(USER_A),
    )
    assert r.json()["research_questions"] == ["How does rainfall affect yield?"]


def test_archive_and_restore(client):
    pid = client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A)).json()["id"]
    client.patch(f"/v1/projects/{pid}", json={"status": "archived"}, headers=as_user(USER_A))

    assert client.get("/v1/projects", headers=as_user(USER_A)).json() == []
    archived = client.get("/v1/projects?archived=true", headers=as_user(USER_A)).json()
    assert [p["id"] for p in archived] == [pid]

    r = client.patch(f"/v1/projects/{pid}", json={"status": "active"}, headers=as_user(USER_A))
    assert r.json()["status"] == "active"


def test_users_cannot_access_each_others_projects(client):
    pid = client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A)).json()["id"]

    assert client.get("/v1/projects", headers=as_user(USER_B)).json() == []
    assert client.get(f"/v1/projects/{pid}", headers=as_user(USER_B)).status_code == 404
    assert (
        client.patch(f"/v1/projects/{pid}", json={"name": "x"}, headers=as_user(USER_B)).status_code
        == 404
    )
    assert client.delete(f"/v1/projects/{pid}", headers=as_user(USER_B)).status_code == 404
    # Still intact for the owner
    assert (
        client.get(f"/v1/projects/{pid}", headers=as_user(USER_A)).json()["name"]
        == NEW_PROJECT["name"]
    )


def test_free_plan_project_limit(client):
    for _ in range(3):
        assert (
            client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A)).status_code
            == 201
        )
    r = client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A))
    assert r.status_code == 402
    assert r.json()["metric"] == "active_projects"
    assert r.json()["limit"] == 3


def test_archived_projects_free_capacity(client):
    ids = [
        client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A)).json()["id"]
        for _ in range(3)
    ]
    client.patch(f"/v1/projects/{ids[0]}", json={"status": "archived"}, headers=as_user(USER_A))
    assert client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A)).status_code == 201
    # Restoring would exceed the limit
    r = client.patch(f"/v1/projects/{ids[0]}", json={"status": "active"}, headers=as_user(USER_A))
    assert r.status_code == 402


def test_delete_project(client):
    pid = client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A)).json()["id"]
    assert client.delete(f"/v1/projects/{pid}", headers=as_user(USER_A)).status_code == 204
    assert client.get(f"/v1/projects/{pid}", headers=as_user(USER_A)).status_code == 404


def test_project_ai_suggestions(client, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")

    # 1. Pre-creation suggestions (/v1/projects/suggest)
    s1 = client.post(
        "/v1/projects/suggest",
        json={
            "name": "AI in Agriculture",
            "topic": "Satellite crop yield prediction for smallholder maize farmers",
            "discipline": "Agricultural Economics",
            "research_level": "postgraduate",
        },
        headers=as_user(USER_A),
    )
    assert s1.status_code == 200, s1.text
    body = s1.json()
    assert len(body["refined_description"]) > 30
    assert len(body["research_questions"]) >= 3
    assert len(body["objectives"]) >= 3
    assert len(body["keywords"]) >= 3

    # 2. Existing project suggestions (/v1/projects/{id}/suggest)
    pid = client.post("/v1/projects", json=NEW_PROJECT, headers=as_user(USER_A)).json()["id"]
    s2 = client.post(f"/v1/projects/{pid}/suggest", headers=as_user(USER_A))
    assert s2.status_code == 200
    assert len(s2.json()["research_questions"]) >= 3
