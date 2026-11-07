import os
import uuid

os.environ["ENV"] = "test"

import pytest
from fastapi import Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import CurrentUser, get_current_user
from app.core.db import Base, get_db
from app.main import app
from app.modules.billing.service import seed_plans

USER_A = uuid.UUID("00000000-0000-0000-0000-00000000000a")
USER_B = uuid.UUID("00000000-0000-0000-0000-00000000000b")


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with TestSession() as s:
        seed_plans(s)

    def _db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    def _user(x_test_user: str | None = Header(default=None)):
        if not x_test_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return CurrentUser(id=uuid.UUID(x_test_user), email=f"{x_test_user[-1]}@test.dev")

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def as_user(user_id: uuid.UUID) -> dict:
    return {"X-Test-User": str(user_id)}
