from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.core.deps import DbSession, require_roles
from app.models.enums import UserRole, WebhookEventStatus
from app.models.user import User
from app.models.webhook_event import WebhookEvent

router = APIRouter(prefix="/api/admin", tags=["admin"])


class WebhookEventPublic(BaseModel):
    id: UUID
    event_key: str
    mp_payment_id: str
    status: WebhookEventStatus
    attempts: int
    last_error: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/webhook-events", response_model=list[WebhookEventPublic])
def list_webhook_events(
    db: DbSession,
    user: User = Depends(require_roles(UserRole.admin)),
    status_filter: WebhookEventStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[WebhookEvent]:
    _ = user
    q = db.query(WebhookEvent).order_by(WebhookEvent.created_at.desc())
    if status_filter is not None:
        q = q.filter(WebhookEvent.status == status_filter)
    return q.limit(limit).all()


@router.get("/webhook-events/stats")
def webhook_event_stats(
    db: DbSession,
    user: User = Depends(require_roles(UserRole.admin)),
) -> dict[str, Any]:
    _ = user
    counts: dict[str, int] = {s.value: 0 for s in WebhookEventStatus}
    for status, n in (
        db.query(WebhookEvent.status, func.count(WebhookEvent.id))
        .group_by(WebhookEvent.status)
        .all()
    ):
        key = status.value if hasattr(status, "value") else str(status)
        counts[key] = int(n)
    return {
        "by_status": counts,
        "failed": counts.get(WebhookEventStatus.falhou.value, 0),
    }
