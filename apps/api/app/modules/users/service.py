from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.modules.users.models import Profile
from app.modules.users.schemas import ProfileUpdate


def get_or_create_profile(db: Session, user: CurrentUser) -> Profile:
    profile = db.get(Profile, user.id)
    if profile is None:
        profile = Profile(id=user.id, email=user.email)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    elif user.email and profile.email != user.email:
        profile.email = user.email
        db.commit()
    return profile


def update_profile(db: Session, profile: Profile, data: ProfileUpdate) -> Profile:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


def delete_account_data(db: Session, profile: Profile) -> None:
    """Delete all application data owned by the user.

    Project-owned rows cascade via foreign keys. Stored files and the Supabase
    auth user are removed by the account-deletion job (added with storage in week 4).
    """
    from app.modules.billing.models import Subscription, UsageCounter
    from app.modules.projects.models import Project

    db.query(Project).filter(Project.owner_id == profile.id).delete()
    db.query(UsageCounter).filter(UsageCounter.user_id == profile.id).delete()
    db.query(Subscription).filter(Subscription.user_id == profile.id).delete()
    db.delete(profile)
    db.commit()
