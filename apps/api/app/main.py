import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import all models so SQLAlchemy metadata is complete.
from app import models  # noqa: F401
from app.core.config import get_settings
from app.modules.assistant.router import router as assistant_router
from app.modules.billing.router import router as billing_router
from app.modules.billing.service import QuotaExceeded
from app.modules.discovery.router import router as discovery_router
from app.modules.library.router import router as library_router
from app.modules.literature.router import router as literature_router
from app.modules.projects.router import router as projects_router
from app.modules.users.router import router as users_router
from app.modules.writing.router import router as writing_router

logger = logging.getLogger("moyee")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.env != "test":
        from app.core.db import Base, get_db, get_engine
        from app.modules.billing.service import seed_plans

        try:
            if settings.database_url.startswith("sqlite"):
                Base.metadata.create_all(get_engine())
            db = next(get_db())
            seed_plans(db)
            db.close()
        except Exception:  # pragma: no cover - DB may be unavailable in local dev
            logger.warning("Could not seed plans on startup (database unavailable?)")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(QuotaExceeded)
    async def quota_handler(_: Request, exc: QuotaExceeded):
        return JSONResponse(
            status_code=402,
            content={
                "detail": "Plan limit reached",
                "code": "quota_exceeded",
                "metric": exc.metric,
                "limit": exc.limit,
                "resets_at": exc.resets_at.isoformat() if exc.resets_at else None,
            },
        )

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    for router in (
        users_router,
        projects_router,
        discovery_router,
        library_router,
        assistant_router,
        literature_router,
        writing_router,
        billing_router,
    ):
        app.include_router(router, prefix="/v1")

    return app


app = create_app()
