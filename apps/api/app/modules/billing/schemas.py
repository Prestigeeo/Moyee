from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    price_usd_cents_monthly: int
    price_usd_cents_yearly: int
    limits: dict
    features: dict


class UsageItemOut(BaseModel):
    metric: str
    used: int
    limit: int | None
    period: str | None
    resets_at: datetime | None


class UsageOut(BaseModel):
    plan: PlanOut
    subscription_status: str
    usage: list[UsageItemOut]


class CheckoutInitOut(BaseModel):
    provider: str
    reference: str
    authorization_url: str
    mode: str
