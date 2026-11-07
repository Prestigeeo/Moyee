import hashlib
import hmac
import json
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.modules.billing import service
from app.modules.billing.models import Plan
from app.modules.billing.schemas import CheckoutInitOut, PlanOut, UsageItemOut, UsageOut
from app.modules.library.models import Document
from app.modules.projects.models import Project, ProjectStatus
from app.modules.users.service import get_or_create_profile

router = APIRouter(tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    """Public: used by the pricing page."""
    return db.scalars(select(Plan).order_by(Plan.price_usd_cents_monthly)).all()


@router.get("/me/usage", response_model=UsageOut)
def my_usage(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    get_or_create_profile(db, user)
    active_projects = db.scalar(
        select(func.count())
        .select_from(Project)
        .where(Project.owner_id == user.id, Project.status != ProjectStatus.archived)
    )
    total_docs = db.scalar(
        select(func.count()).select_from(Document).where(Document.owner_id == user.id)
    )
    total_bytes = db.scalar(
        select(func.coalesce(func.sum(Document.file_size_bytes), 0)).where(
            Document.owner_id == user.id
        )
    )
    storage_mb = int(round((total_bytes or 0) / (1024 * 1024)))
    sub = service.get_subscription(db, user.id)
    plan = service.get_plan(db, user.id)
    items = service.usage_summary(
        db,
        user.id,
        {
            "active_projects": active_projects or 0,
            "documents": total_docs or 0,
            "storage_mb": storage_mb,
        },
    )
    return UsageOut(
        plan=PlanOut.model_validate(plan),
        subscription_status=sub.status,
        usage=[UsageItemOut(**asdict(i)) for i in items],
    )


@router.post("/billing/checkout", response_model=CheckoutInitOut)
def init_pro_checkout(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initialise a Paystack test-mode upgrade checkout and activate Pro in test mode."""
    get_or_create_profile(db, user)
    reference = f"moyee_test_{uuid.uuid4().hex[:12]}"
    service.upgrade_to_pro(db, user.id, reference)
    return CheckoutInitOut(
        provider="paystack",
        reference=reference,
        authorization_url=f"https://checkout.paystack.com/{reference}",
        mode="test",
    )


@router.post("/billing/cancel", response_model=UsageOut)
def cancel_my_subscription(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_create_profile(db, user)
    service.cancel_subscription(db, user.id)
    return my_usage(user=user, db=db)


@router.post("/billing/webhooks/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Verify HMAC-SHA512 signature from Paystack and synchronise subscription state."""
    raw_body = await request.body()
    secret = get_settings().paystack_secret_key.encode("utf-8")
    expected = hmac.new(secret, raw_body, hashlib.sha512).hexdigest()
    if not x_paystack_signature or not hmac.compare_digest(expected, x_paystack_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    payload = json.loads(raw_body.decode("utf-8"))
    event_type = payload.get("event")
    data = payload.get("data") or {}
    metadata = data.get("metadata") or {}
    user_id_raw = metadata.get("user_id")
    reference = data.get("reference") or "paystack_webhook"

    if user_id_raw:
        uid = uuid.UUID(str(user_id_raw))
        if event_type in ("charge.success", "subscription.create"):
            service.upgrade_to_pro(db, uid, reference)
        elif event_type in ("subscription.disable", "invoice.payment_failed"):
            service.cancel_subscription(db, uid)

    return {"received": True}
