import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.modules.assistant import service
from app.modules.assistant.schemas import (
    AskQuestionRequest,
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
    FeedbackRequest,
    MessageOut,
)
from app.modules.projects.service import get_owned_project

router = APIRouter(prefix="/projects/{project_id}/conversations", tags=["assistant"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    return service.list_conversations(db, project)


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    project_id: uuid.UUID,
    data: ConversationCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    return service.create_conversation(db, project, data)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, user.id, project_id)
    conv = service.get_owned_conversation(db, user.id, project_id, conversation_id)
    return service.get_conversation_detail(db, conv)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, user.id, project_id)
    conv = service.get_owned_conversation(db, user.id, project_id, conversation_id)
    service.delete_conversation(db, conv)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
def ask_in_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    data: AskQuestionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    conv = service.get_owned_conversation(db, user.id, project_id, conversation_id)
    return service.ask_question(db, project, conv, data)


@router.post("/messages/{message_id}/feedback", response_model=MessageOut)
def give_feedback(
    project_id: uuid.UUID,
    message_id: uuid.UUID,
    data: FeedbackRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, user.id, project_id)
    return service.set_message_feedback(db, user.id, project_id, message_id, data.feedback)
