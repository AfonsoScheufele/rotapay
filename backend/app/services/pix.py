import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException
from redis import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.enums import FreightStatus, PaymentStatus, UserRole, WebhookEventStatus
from app.models.freight import Freight
from app.models.payment import Payment
from app.models.user import User
from app.models.webhook_event import WebhookEvent
from app.queue import get_webhook_queue, webhook_retry
from app.services.freight import get_freight_or_404
from app.services.status_machine import IllegalTransitionError, assert_transition

MP_API = "https://api.mercadopago.com"
logger = get_logger("rotapay.pix")


class RateLimitExceeded(Exception):
    pass


class WebhookApplyError(Exception):
    pass


def _redis() -> Redis | None:
    try:
        client = Redis.from_url(get_settings().redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def check_webhook_rate_limit(ip: str, limit: int = 60, window: int = 60) -> None:
    client = _redis()
    if not client:
        return
    key = f"rl:webhook:{ip}"
    count = client.incr(key)
    if count == 1:
        client.expire(key, window)
    if count > limit:
        raise RateLimitExceeded("Rate limit excedido")


def create_pix_charge(db: Session, user: User, freight_id: uuid.UUID) -> Payment:
    settings = get_settings()
    freight = get_freight_or_404(db, freight_id)

    if user.role == UserRole.embarcador and freight.shipper_id != user.id:
        raise HTTPException(status_code=403, detail="Apenas o embarcador dono")
    if user.role not in (UserRole.embarcador, UserRole.admin):
        raise HTTPException(status_code=403, detail="Sem permissão para gerar Pix")
    if freight.status != FreightStatus.entregue:
        raise HTTPException(
            status_code=409,
            detail="Pix só pode ser gerado quando o frete está entregue",
        )

    existing = (
        db.query(Payment)
        .filter(
            Payment.freight_id == freight.id,
            Payment.deleted_at.is_(None),
            Payment.status == PaymentStatus.pending,
        )
        .first()
    )
    if existing:
        return existing

    if not settings.mp_access_token:
        payment = Payment(
            freight_id=freight.id,
            status=PaymentStatus.pending,
            amount_cents=freight.amount_cents,
            mp_payment_id=f"demo-{uuid.uuid4().hex[:12]}",
            qr_code="00020126580014br.gov.bcb.pix0136demo-rotapay",
            qr_code_base64=None,
            copy_paste=(
                "00020126580014BR.GOV.BCB.PIX0136"
                f"{uuid.uuid4().hex}520400005303986540"
                f"{freight.amount_cents / 100:.2f}"
                "5802BR5925ROTAPAY SANDBOX DEMO6009SAO PAULO62070503***6304ABCD"
            ),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    notification_url = (
        f"{settings.api_public_url.rstrip('/')}/api/webhooks/mercadopago"
        "?source_news=webhooks"
    )
    body = {
        "transaction_amount": round(freight.amount_cents / 100, 2),
        "description": f"Frete RotaPay {freight.id}",
        "payment_method_id": "pix",
        "payer": {
            "email": user.email,
            "first_name": user.name.split()[0] if user.name else "Embarcador",
        },
        "external_reference": str(freight.id),
        "notification_url": notification_url,
    }
    headers = {
        "Authorization": f"Bearer {settings.mp_access_token}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4()),
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{MP_API}/v1/payments", json=body, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Erro Mercado Pago: {resp.text[:300]}",
            )
        data = resp.json()

    tx = data.get("point_of_interaction", {}).get("transaction_data", {})
    payment = Payment(
        freight_id=freight.id,
        status=PaymentStatus.pending,
        amount_cents=freight.amount_cents,
        mp_payment_id=str(data["id"]),
        qr_code=tx.get("qr_code"),
        qr_code_base64=tx.get("qr_code_base64"),
        copy_paste=tx.get("qr_code"),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def verify_mp_signature(
    *,
    x_signature: str | None,
    x_request_id: str | None,
    data_id: str | None,
) -> bool:
    settings = get_settings()
    if not settings.mp_webhook_secret:
        return settings.environment == "development"
    if not x_signature or not data_id:
        return False

    parts = dict(
        p.split("=", 1) for p in x_signature.split(",") if "=" in p
    )
    ts = parts.get("ts")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False

    manifest = f"id:{data_id};request-id:{x_request_id or ''};ts:{ts};"
    expected = hmac.new(
        settings.mp_webhook_secret.encode(),
        manifest.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, v1)


def fetch_mp_payment(mp_payment_id: str) -> dict:
    settings = get_settings()
    if not settings.mp_access_token:
        return {
            "id": mp_payment_id,
            "status": "approved",
            "external_reference": None,
        }

    headers = {"Authorization": f"Bearer {settings.mp_access_token}"}
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(f"{MP_API}/v1/payments/{mp_payment_id}", headers=headers)
        resp.raise_for_status()
        return resp.json()


def enqueue_webhook_event(event_id: uuid.UUID) -> None:
    from rq.job import Callback

    from app.queue.jobs import on_webhook_job_failure, process_webhook_job

    queue = get_webhook_queue()
    queue.enqueue(
        process_webhook_job,
        str(event_id),
        job_id=f"webhook-{event_id}",
        retry=webhook_retry(),
        on_failure=Callback(on_webhook_job_failure),
        result_ttl=3600,
        failure_ttl=86400,
    )


def accept_webhook(
    db: Session,
    *,
    payload: dict,
    ip: str,
    x_signature: str | None = None,
    x_request_id: str | None = None,
) -> dict[str, Any]:
    try:
        check_webhook_rate_limit(ip)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    topic = payload.get("type") or payload.get("topic") or "payment"
    action = payload.get("action") or "updated"
    data = payload.get("data") or {}
    mp_payment_id = str(data.get("id") or payload.get("data.id") or "")
    if not mp_payment_id:
        return {"ok": True, "skipped": "missing payment id"}

    if not verify_mp_signature(
        x_signature=x_signature,
        x_request_id=x_request_id,
        data_id=mp_payment_id,
    ):
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    event_key = f"{topic}:{mp_payment_id}:{action}"
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()

    event = WebhookEvent(
        event_key=event_key,
        mp_payment_id=mp_payment_id,
        payload_hash=payload_hash,
        status=WebhookEventStatus.recebido,
        attempts=0,
        raw_payload=payload,
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info(
            "webhook_accept_duplicate",
            extra={
                "event_key": event_key,
                "mp_payment_id": mp_payment_id,
                "result": "duplicate",
            },
        )
        return {"ok": True, "duplicate": True}

    db.commit()
    db.refresh(event)

    try:
        enqueue_webhook_event(event.id)
    except Exception as exc:
        logger.info(
            "webhook_enqueue_failed",
            extra={
                "event_id": str(event.id),
                "event_key": event_key,
                "result": "enqueue_failed",
            },
        )
        raise HTTPException(
            status_code=503,
            detail="Fila indisponível; evento persistido como recebido",
        ) from exc

    logger.info(
        "webhook_accepted",
        extra={
            "event_id": str(event.id),
            "event_key": event_key,
            "mp_payment_id": mp_payment_id,
            "result": "accepted",
        },
    )
    return {
        "ok": True,
        "accepted": True,
        "event_id": str(event.id),
        "duplicate": False,
    }


def apply_webhook_event(db: Session, event: WebhookEvent) -> dict[str, Any]:
    payload = event.raw_payload or {}
    mp_payment_id = event.mp_payment_id

    payment = (
        db.query(Payment)
        .filter(Payment.mp_payment_id == mp_payment_id, Payment.deleted_at.is_(None))
        .first()
    )

    mp_data = fetch_mp_payment(mp_payment_id)
    mp_status = mp_data.get("status")

    if not payment:
        ext = mp_data.get("external_reference")
        if ext:
            freight = db.query(Freight).filter(Freight.id == uuid.UUID(str(ext))).first()
            if freight:
                payment = (
                    db.query(Payment)
                    .filter(
                        Payment.freight_id == freight.id,
                        Payment.deleted_at.is_(None),
                        Payment.status == PaymentStatus.pending,
                    )
                    .first()
                )
                if payment and not payment.mp_payment_id:
                    payment.mp_payment_id = mp_payment_id

    if not payment:
        return {
            "ok": True,
            "skipped": "payment not found",
            "event_key": event.event_key,
        }

    freight = payment.freight or get_freight_or_404(db, payment.freight_id)

    if mp_status == "approved":
        payment.status = PaymentStatus.approved
        payment.paid_at = datetime.now(timezone.utc)
        payment.driver_payout_recorded_cents = freight.driver_net_cents
        try:
            assert_transition(freight.status, FreightStatus.pago)
            freight.status = FreightStatus.pago
        except IllegalTransitionError as exc:
            raise WebhookApplyError(
                f"Transição ilegal para pago: {freight.status.value}"
            ) from exc
    elif mp_status in ("rejected", "cancelled"):
        payment.status = (
            PaymentStatus.rejected
            if mp_status == "rejected"
            else PaymentStatus.cancelled
        )

    db.flush()
    return {
        "ok": True,
        "payment_id": str(payment.id),
        "freight_id": str(freight.id),
        "freight_status": freight.status.value,
        "event_key": event.event_key,
        "duplicate": False,
    }


def process_webhook(
    db: Session,
    *,
    payload: dict,
    ip: str,
    x_signature: str | None = None,
    x_request_id: str | None = None,
) -> dict:
    return accept_webhook(
        db,
        payload=payload,
        ip=ip,
        x_signature=x_signature,
        x_request_id=x_request_id,
    )
