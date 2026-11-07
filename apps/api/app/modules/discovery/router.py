from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.modules.billing import service as billing
from app.modules.discovery import service
from app.modules.discovery.schemas import DiscoveredWork, DiscoverySearchResponse
from app.modules.users.service import get_or_create_profile

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/search", response_model=DiscoverySearchResponse)
def search_academic_works(
    q: str = Query(min_length=2, max_length=300),
    provider: str = Query(default="openalex", max_length=32),
    year_from: int | None = Query(default=None, ge=1800, le=2100),
    year_to: int | None = Query(default=None, ge=1800, le=2100),
    open_access_only: bool = False,
    publication_type: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1, le=500),
    per_page: int = Query(default=25, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_create_profile(db, user)
    billing.consume(db, user.id, "academic_searches")
    return service.search_works(
        q,
        provider=provider,
        year_from=year_from,
        year_to=year_to,
        open_access_only=open_access_only,
        publication_type=publication_type,
        page=page,
        per_page=per_page,
    )


@router.get("/doi", response_model=DiscoveredWork)
def resolve_doi(
    doi: str = Query(min_length=5, max_length=255),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_create_profile(db, user)
    billing.consume(db, user.id, "academic_searches")
    work = service.lookup_by_doi(doi)
    if work is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DOI not found")
    return work
