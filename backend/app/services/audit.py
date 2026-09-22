
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

def write_audit(
    db: Session,
    *,
    actor_id: UUID,
    action: str,
    freight_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        freight_id=freight_id,
        action=action,
        metadata_=metadata,
    )
    db.add(entry)
    return entry
