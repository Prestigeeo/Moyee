from app.ai import gateway
from app.core.config import get_settings

PASSAGES = [{
    "marker_id": "S1", "source_title": "Banking study", "page_number": 1,
    "text_content": (
        "Students reported using mobile banking frequently."
        "Perceived security was associated with satisfaction."
    ),
}]
QUESTION = "based on the research topic and sources..generate potential research questions"


def generate(question=QUESTION):
    return gateway.generate_grounded_response(
        question=question, mode="qa", project_name="Banking",
        project_topic="mobile banking adoption", research_questions=[], passages=PASSAGES,
    )


def test_no_provider_returns_honest_question_templates(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    result = generate()
    assert result.provider == "extractive"
    assert "template-based" in result.answer_with_markers
    assert result.answer_with_markers.count("?") == 3
    assert "mobile banking adoption" in result.answer_with_markers
    assert "[S1]" not in result.answer_with_markers
    assert "not a synthesis" in result.answer_with_markers


def test_provider_prose_is_rejected_and_next_provider_generates_questions(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "test")
    monkeypatch.setattr(settings, "groq_api_key", "test")
    monkeypatch.setattr(gateway, "_call_gemini", lambda *a: {"answer": "Copied abstract."})

    def groq(system, user, *args):
        assert "numbered" in system
        assert "mobile banking adoption" in user
        return {"answer": "1. How is security associated with adoption?\nRationale: [S1]"}

    monkeypatch.setattr(gateway, "_call_groq", groq)
    assert generate().provider == "groq"


def test_provider_failure_returns_labelled_fallback(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "test")
    monkeypatch.setattr(settings, "groq_api_key", "")

    def fail(*args):
        raise RuntimeError("unavailable")

    monkeypatch.setattr(gateway, "_call_gemini", fail)
    result = generate()
    assert result.provider == "extractive"
    assert "Limited mode" in result.limitations


def test_excerpts_split_missing_spaces_and_do_not_claim_to_answer():
    result = gateway._extractive_fallback("security satisfaction", "qa", "Banking", PASSAGES)
    assert "Perceived security" in result.answer_with_markers
    assert "Students reported" not in result.answer_with_markers
    assert "Related source excerpts" in result.answer_with_markers
    assert "rather than a generated answer" in result.limitations


def test_existing_question_lookup_is_not_treated_as_generation():
    assert not gateway.requests_research_questions("What research questions did the authors ask?")
