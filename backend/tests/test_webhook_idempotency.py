from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.enums import FreightStatus, PaymentStatus, WebhookEventStatus
from app.models.webhook_event import WebhookEvent
from app.services.pix import accept_webhook, apply_webhook_event


@pytest.fixture
def freight_and_payment():
    freight_id = uuid4()
    freight = MagicMock()
    freight.id = freight_id
    freight.status = FreightStatus.entregue
    freight.driver_net_cents = 95_000

    payment = MagicMock()
    payment.id = uuid4()
    payment.freight_id = freight_id
    payment.freight = freight
    payment.status = PaymentStatus.pending
    payment.mp_payment_id = "123456789"
    payment.deleted_at = None
    return freight, payment


def test_accept_webhook_duplicado_retorna_duplicate() -> None:
    db = MagicMock()

    def flush_side_effect() -> None:
        raise IntegrityError("stmt", "params", Exception("unique"))

    db.flush.side_effect = flush_side_effect

    with patch("app.services.pix.check_webhook_rate_limit"), patch(
        "app.services.pix.verify_mp_signature", return_value=True
    ):
        result = accept_webhook(
            db,
            payload={
                "type": "payment",
                "action": "payment.updated",
                "data": {"id": "123456789"},
            },
            ip="127.0.0.1",
        )

    assert result["ok"] is True
    assert result.get("duplicate") is True
    db.rollback.assert_called()


def test_apply_webhook_aprova_e_marca_pago(freight_and_payment) -> None:
    freight, payment = freight_and_payment
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = payment

    event = WebhookEvent(
        event_key="payment:123456789:payment.updated",
        mp_payment_id="123456789",
        payload_hash="abc",
        status=WebhookEventStatus.processando,
        raw_payload={
            "type": "payment",
            "action": "payment.updated",
            "data": {"id": "123456789"},
        },
    )

    with patch(
        "app.services.pix.fetch_mp_payment",
        return_value={"id": "123456789", "status": "approved"},
    ):
        result = apply_webhook_event(db, event)

    assert result["ok"] is True
    assert payment.status == PaymentStatus.approved
    assert freight.status == FreightStatus.pago
    assert payment.driver_payout_recorded_cents == 95_000
