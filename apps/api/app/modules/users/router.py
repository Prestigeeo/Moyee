from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.modules.users import service
from app.modules.users.schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=ProfileOut)
def read_me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.get_or_create_profile(db, user)


@router.patch("", response_model=ProfileOut)
def update_me(
    data: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = service.get_or_create_profile(db, user)
    return service.update_profile(db, profile, data)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = service.get_or_create_profile(db, user)
    service.delete_account_data(db, profile)
