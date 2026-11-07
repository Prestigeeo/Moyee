"""Grounded RAG assistant orchestration & citation validator (PRD §6.7, §9.2)."""

import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gateway import (
    generate_grounded_response,
    requests_project_guidance,
    requests_research_questions,
)
from app.modules.assistant.models import Conversation, Message, MessageCitation
from app.modules.assistant.schemas import (
    AskQuestionRequest,
    CitationOut,
    ConversationCreate,
    ConversationDetailOut,
    MessageOut,
)
from app.modules.billing import service as billing
from app.modules.projects.models import Project
from app.modules.retrieval.service import retrieve_project_passages

MARKER_REGEX = re.compile(r"\[(S\d+|\d+)\]")


def validate_and_renumber_citations(
    raw_answer: str, passages: list[dict]
) -> tuple[str, list[dict]]:
    """Verify every inline `[S#]` marker against `passages`.

    - Any marker not present in `passages` is stripped immediately (zero fabricated citations).
    - Valid markers are renumbered sequentially `[1]`, `[2]`, ... in order of first appearance.
    """
    by_marker = {p["marker_id"]: p for p in passages}
    by_index = {str(i + 1): p for i, p in enumerate(passages)}

    assigned_numbers: dict[str, int] = {}
    ordered_citations: list[dict] = []

    def _replace(match: re.Match[str]) -> str:
        token = match.group(1)
        passage = by_marker.get(token) or by_index.get(token)
        if passage is None:
            return ""
        m_id = passage["marker_id"]
        if m_id not in assigned_numbers:
            num = len(ordered_citations) + 1
            assigned_numbers[m_id] = num
            ordered_citations.append({"citation_number": num, **passage})
        return f"[{assigned_numbers[m_id]}]"

    cleaned = MARKER_REGEX.sub(_replace, raw_answer)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, ordered_citations


def _message_to_out(db: Session, msg: Message) -> MessageOut:
    cites = db.scalars(
        select(MessageCitation)
        .where(MessageCitation.message_id == msg.id)
        .order_by(MessageCitation.citation_number)
    ).all()
    return MessageOut(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        interpretation=msg.interpretation,
        limitations=msg.limitations,
        suggested_actions=msg.suggested_actions or [],
        insufficient_evidence=msg.insufficient_evidence,
        feedback=msg.feedback,
        provider=msg.provider,
        model=msg.model,
        citations=[CitationOut.model_validate(c) for c in cites],
        created_at=msg.created_at,
    )


def list_conversations(db: Session, project: Project) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.project_id == project.id, Conversation.owner_id == project.owner_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_conversation(db: Session, project: Project, data: ConversationCreate) -> Conversation:
    conv = Conversation(
        project_id=project.id,
        owner_id=project.owner_id,
        title=data.title.strip(),
        mode=data.mode,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_owned_conversation(
    db: Session, owner_id: uuid.UUID, project_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    conv = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.project_id == project_id,
            Conversation.owner_id == owner_id,
        )
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


def get_conversation_detail(db: Session, conv: Conversation) -> ConversationDetailOut:
    msgs = db.scalars(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc())
    ).all()
    return ConversationDetailOut(
        id=conv.id,
        project_id=conv.project_id,
        title=conv.title,
        mode=conv.mode,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[_message_to_out(db, m) for m in msgs],
    )


def delete_conversation(db: Session, conv: Conversation) -> None:
    db.delete(conv)
    db.commit()


def ask_question(
    db: Session,
    project: Project,
    conv: Conversation,
    req: AskQuestionRequest,
) -> MessageOut:
    billing.consume(db, project.owner_id, "assistant_messages")

    user_msg = Message(
        conversation_id=conv.id,
        project_id=project.id,
        owner_id=project.owner_id,
        role="user",
        content=req.question.strip(),
    )
    db.add(user_msg)
    if conv.title == "New Research Conversation":
        conv.title = req.question.strip()[:80]
    conv.mode = req.mode
    db.flush()

    is_guidance = requests_project_guidance(req.question, req.mode)
    retrieval_query = req.question
    if requests_research_questions(req.question):
        retrieval_query = " ".join(
            [project.topic or project.name, *(project.research_questions or [])]
        )
    elif is_guidance:
        retrieval_query = " ".join(
            [req.question, project.topic or project.name, *(project.research_questions or [])]
        )
    passages = retrieve_project_passages(
        db, project, retrieval_query, source_ids=req.source_ids, top_k=6
    )

    if not passages and not is_guidance:
        assistant_msg = Message(
            conversation_id=conv.id,
            project_id=project.id,
            owner_id=project.owner_id,
            role="assistant",
            content=(
                "Not enough evidence in your project sources to answer this question with "
                "verified citations."
            ),
            interpretation=(
                f"To explore '{req.question.strip()[:90]}' in the context of '{project.topic}', "
                "search Academic Discovery for relevant studies or upload full-text PDFs to "
                "your project library."
            ),
            limitations="Zero matching passages were found in the selected project scope.",
            suggested_actions=[
                "Search Academic Discovery for papers on this topic",
                "Upload full-text PDFs to your Project Library",
            ],
            insufficient_evidence=True,
            provider="moyee",
            model="evidence-guard",
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        return _message_to_out(db, assistant_msg)

    ai_resp = generate_grounded_response(
        question=req.question,
        mode=req.mode,
        project_name=project.name,
        project_topic=project.topic,
        research_questions=project.research_questions or [],
        passages=passages,
    )
    validated_text, verified_citations = validate_and_renumber_citations(
        ai_resp.answer_with_markers, passages
    )

    assistant_msg = Message(
        conversation_id=conv.id,
        project_id=project.id,
        owner_id=project.owner_id,
        role="assistant",
        content=validated_text,
        interpretation=ai_resp.interpretation,
        limitations=ai_resp.limitations,
        suggested_actions=ai_resp.suggested_actions,
        insufficient_evidence=len(passages) == 0,
        provider=ai_resp.provider,
        model=ai_resp.model,
    )
    db.add(assistant_msg)
    db.flush()

    for c in verified_citations:
        db.add(
            MessageCitation(
                message_id=assistant_msg.id,
                citation_number=c["citation_number"],
                project_source_id=c["project_source_id"],
                chunk_id=c["chunk_id"],
                source_title=c["source_title"],
                inline_label=c["inline_label"],
                page_number=c["page_number"],
                quote=c["text_content"][:320],
            )
        )

    db.commit()
    db.refresh(assistant_msg)
    return _message_to_out(db, assistant_msg)


def set_message_feedback(
    db: Session, owner_id: uuid.UUID, project_id: uuid.UUID, message_id: uuid.UUID, feedback: int
) -> MessageOut:
    msg = db.scalar(
        select(Message).where(
            Message.id == message_id,
            Message.project_id == project_id,
            Message.owner_id == owner_id,
        )
    )
    if msg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    msg.feedback = feedback
    db.commit()
    db.refresh(msg)
    return _message_to_out(db, msg)
