from uuid import UUID

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.enums import WebhookEventStatus
from app.models.webhook_event import WebhookEvent
from app.queue.settings import WEBHOOK_MAX_RETRIES
from app.services import pix as pix_svc

logger = get_logger("rotapay.queue")


def mark_webhook_failed(event_id: str, error_message: str) -> None:
    db = SessionLocal()
    try:
        event = db.get(WebhookEvent, UUID(event_id))
        if not event:
            return
        if event.status == WebhookEventStatus.processado:
            return
        event.status = WebhookEventStatus.falhou
        event.last_error = error_message[:500]
        db.commit()
        logger.info(
            "webhook_job_failed_final",
            extra={
                "event_id": event_id,
                "event_key": event.event_key,
                "attempt": event.attempts,
                "result": "falhou",
            },
        )
    finally:
        db.close()


def on_webhook_job_failure(job, connection, type, value, traceback):  # noqa: A002
    event_id = job.args[0] if job.args else None
    if not event_id:
        return
    mark_webhook_failed(str(event_id), f"{type.__name__}: {value}" if type else str(value))


def process_webhook_job(event_id: str) -> dict:
    db = SessionLocal()
    try:
        event = db.get(WebhookEvent, UUID(event_id))
        if not event:
            logger.info(
                "webhook_job_missing_event",
                extra={"event_id": event_id, "result": "missing"},
            )
            return {"ok": False, "reason": "missing"}

        if event.status == WebhookEventStatus.processado:
            logger.info(
                "webhook_job_already_done",
                extra={
                    "event_id": event_id,
                    "event_key": event.event_key,
                    "result": "already_processado",
                },
            )
            return {"ok": True, "duplicate": True}

        event.status = WebhookEventStatus.processando
        event.attempts = (event.attempts or 0) + 1
        event.last_error = None
        db.commit()

        attempt = event.attempts
        event_key = event.event_key
        logger.info(
            "webhook_job_start",
            extra={
                "event_id": event_id,
                "event_key": event_key,
                "attempt": attempt,
                "mp_payment_id": event.mp_payment_id,
                "result": "processando",
            },
        )

        try:
            result = pix_svc.apply_webhook_event(db, event)
            event.status = WebhookEventStatus.processado
            from datetime import datetime, timezone

            event.processed_at = datetime.now(timezone.utc)
            event.last_error = None
            db.commit()
            logger.info(
                "webhook_job_done",
                extra={
                    "event_id": event_id,
                    "event_key": event_key,
                    "attempt": attempt,
                    "freight_id": result.get("freight_id"),
                    "payment_id": result.get("payment_id"),
                    "result": "processado",
                },
            )
            return result
        except Exception as exc:
            db.rollback()
            event = db.get(WebhookEvent, UUID(event_id))
            if event:
                event.last_error = str(exc)[:500]
                if event.attempts >= WEBHOOK_MAX_RETRIES + 1:
                    event.status = WebhookEventStatus.falhou
                else:
                    event.status = WebhookEventStatus.recebido
                db.commit()
            logger.info(
                "webhook_job_error",
                extra={
                    "event_id": event_id,
                    "event_key": event_key,
                    "attempt": attempt,
                    "result": "retry" if attempt <= WEBHOOK_MAX_RETRIES else "falhou",
                },
            )
            raise
    finally:
        db.close()
