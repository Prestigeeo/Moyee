"""Plans, usage metering and entitlement enforcement."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.billing.models import Plan, Subscription, UsageCounter

Period = Literal["day", "month"]

# Metered actions that reset on a period. Limits live in Plan.limits under the same key.
PERIODIC_METRICS: dict[str, Period] = {
    "assistant_messages": "day",
    "academic_searches": "day",
    "writing_ai_actions": "day",
    "document_summaries": "month",
}

# Default plan configuration (MVP spec §4). `None` = unlimited.
DEFAULT_PLANS: list[dict] = [
    {
        "id": "free",
        "name": "Free",
        "price_usd_cents_monthly": 0,
        "price_usd_cents_yearly": 0,
        "limits": {
            "active_projects": 3,
            "documents": 15,
            "storage_mb": 100,
            "max_file_mb": 10,
            "assistant_messages": 20,
            "academic_searches": 30,
            "document_summaries": 10,
            "writing_ai_actions": 15,
            "matrices_per_project": 1,
            "matrix_sources": 5,
        },
        "features": {
            "citation_styles": ["apa7", "harvard", "ieee"],
            "exports": ["docx", "bibtex", "csv"],
        },
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_usd_cents_monthly": 1000,
        "price_usd_cents_yearly": 9600,
        "limits": {
            "active_projects": None,
            "documents": 300,
            "storage_mb": 5120,
            "max_file_mb": 20,
            "assistant_messages": 300,
            "academic_searches": None,
            "document_summaries": 200,
            "writing_ai_actions": 200,
            "matrices_per_project": None,
            "matrix_sources": 15,
        },
        "features": {
            "citation_styles": ["apa7", "harvard", "ieee", "mla", "chicago"],
            "exports": ["docx", "bibtex", "csv", "pdf", "ris"],
        },
    },
]


class QuotaExceeded(Exception):
    def __init__(self, metric: str, limit: int, resets_at: datetime | None):
        self.metric = metric
        self.limit = limit
        self.resets_at = resets_at
        super().__init__(f"Quota exceeded for {metric}")


@dataclass
class UsageItem:
    metric: str
    used: int
    limit: int | None
    period: Period | None
    resets_at: datetime | None


def seed_plans(db: Session) -> None:
    """Insert or update default plans. Idempotent."""
    for data in DEFAULT_PLANS:
        plan = db.get(Plan, data["id"])
        if plan is None:
            db.add(Plan(**data))
        else:
            for key, value in data.items():
                setattr(plan, key, value)
    db.commit()


def _period_start(period: Period, today: date | None = None) -> date:
    today = today or datetime.now(UTC).date()
    return today if period == "day" else today.replace(day=1)


def _period_reset(period: Period, start: date) -> datetime:
    if period == "day":
        nxt = start + timedelta(days=1)
    else:
        nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return datetime.combine(nxt, time.min, tzinfo=UTC)


def get_subscription(db: Session, user_id: uuid.UUID) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
    if sub is None:
        sub = Subscription(user_id=user_id, plan_id="free", status="active")
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def get_plan(db: Session, user_id: uuid.UUID) -> Plan:
    sub = get_subscription(db, user_id)
    plan_id = sub.plan_id if sub.status == "active" else "free"
    plan = db.get(Plan, plan_id)
    if plan is None:
        seed_plans(db)
        plan = db.get(Plan, plan_id)
    assert plan is not None
    return plan


def get_limit(db: Session, user_id: uuid.UUID, metric: str) -> int | None:
    return get_plan(db, user_id).limits.get(metric)


def consume(db: Session, user_id: uuid.UUID, metric: str, amount: int = 1) -> None:
    """Atomically consume `amount` of a periodic quota, or raise QuotaExceeded."""
    period = PERIODIC_METRICS[metric]
    limit = get_limit(db, user_id, metric)
    start = _period_start(period)

    exists = db.scalar(
        select(UsageCounter.id).where(
            UsageCounter.user_id == user_id,
            UsageCounter.metric == metric,
            UsageCounter.period_start == start,
        )
    )
    if exists is None:
        try:
            db.add(UsageCounter(user_id=user_id, metric=metric, period_start=start, count=0))
            db.commit()
        except IntegrityError:
            db.rollback()  # created concurrently

    stmt = (
        update(UsageCounter)
        .where(
            UsageCounter.user_id == user_id,
            UsageCounter.metric == metric,
            UsageCounter.period_start == start,
        )
        .values(count=UsageCounter.count + amount)
    )
    if limit is not None:
        stmt = stmt.where(UsageCounter.count + amount <= limit)
    result = db.execute(stmt)
    db.commit()
    if result.rowcount == 0:
        raise QuotaExceeded(metric, limit or 0, _period_reset(period, start))


def ensure_capacity(
    db: Session, user_id: uuid.UUID, metric: str, current: int, adding: int = 1
) -> None:
    """Check a count-based limit (e.g. active projects) before creating something."""
    limit = get_limit(db, user_id, metric)
    if limit is not None and current + adding > limit:
        raise QuotaExceeded(metric, limit, None)


def usage_summary(db: Session, user_id: uuid.UUID, counts: dict[str, int]) -> list[UsageItem]:
    """Usage for all metrics. `counts` supplies current values of count-based metrics."""
    plan = get_plan(db, user_id)
    items: list[UsageItem] = []
    for metric, period in PERIODIC_METRICS.items():
        start = _period_start(period)
        used = db.scalar(
            select(UsageCounter.count).where(
                UsageCounter.user_id == user_id,
                UsageCounter.metric == metric,
                UsageCounter.period_start == start,
            )
        )
        items.append(
            UsageItem(
                metric, used or 0, plan.limits.get(metric), period, _period_reset(period, start)
            )
        )
    for metric, used in counts.items():
        items.append(UsageItem(metric, used, plan.limits.get(metric), None, None))
    return items


def upgrade_to_pro(db: Session, user_id: uuid.UUID, reference: str) -> Subscription:
    """Activate Pro for `user_id` via verified Paystack webhook or test checkout."""
    seed_plans(db)
    sub = get_subscription(db, user_id)
    sub.plan_id = "pro"
    sub.status = "active"
    sub.provider = "paystack"
    sub.provider_subscription_id = reference
    sub.current_period_end = datetime.now(UTC) + timedelta(days=30)
    db.commit()
    db.refresh(sub)
    return sub


def cancel_subscription(db: Session, user_id: uuid.UUID) -> Subscription:
    sub = get_subscription(db, user_id)
    sub.plan_id = "free"
    sub.status = "cancelled"
    db.commit()
    db.refresh(sub)
    return sub
