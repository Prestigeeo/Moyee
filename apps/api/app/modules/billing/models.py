import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONType, TimestampMixin


class Plan(TimestampMixin, Base):
    """Plan configuration. Limits are data, so they can change without a deploy."""

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # "free", "pro"
    name: Mapped[str] = mapped_column(String(64))
    price_usd_cents_monthly: Mapped[int] = mapped_column(Integer, default=0)
    price_usd_cents_yearly: Mapped[int] = mapped_column(Integer, default=0)
    # {"metric": int | null}. null means unlimited.
    limits: Mapped[dict] = mapped_column(JSONType, default=dict)
    features: Mapped[dict] = mapped_column(JSONType, default=dict)


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, index=True
    )
    plan_id: Mapped[str] = mapped_column(String(32), ForeignKey("plans.id"), default="free")
    # active | past_due | cancelled
    status: Mapped[str] = mapped_column(String(32), default="active")
    provider: Mapped[str | None] = mapped_column(String(32))
    provider_customer_id: Mapped[str | None] = mapped_column(String(128))
    provider_subscription_id: Mapped[str | None] = mapped_column(String(128))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsageCounter(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("user_id", "metric", "period_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    metric: Mapped[str] = mapped_column(String(64))
    period_start: Mapped[date] = mapped_column(Date)
    count: Mapped[int] = mapped_column(Integer, default=0)
