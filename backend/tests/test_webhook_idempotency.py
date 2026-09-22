
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.enums import FreightStatus, PaymentStatus
from app.services.pix import process_webhook

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

def test_webhook_duplicado_retorna_duplicate(freight_and_payment) -> None:
    freight, payment = freight_and_payment
    db = MagicMock()

    call_count = {"n": 0}

    def flush_side_effect() -> None:
        call_count["n"] += 1
        if call_count["n"] >= 1:
            raise IntegrityError("stmt", "params", Exception("unique"))

    db.flush.side_effect = flush_side_effect
    db.query.return_value.filter.return_value.first.return_value = payment

    with patch("app.services.pix.check_webhook_rate_limit"), patch(
        "app.services.pix.verify_mp_signature", return_value=True
    ):
        result = process_webhook(
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

def test_webhook_aprova_e_marca_pago(freight_and_payment) -> None:
    freight, payment = freight_and_payment
    db = MagicMock()
    db.flush.return_value = None
    db.query.return_value.filter.return_value.first.return_value = payment

    with patch("app.services.pix.check_webhook_rate_limit"), patch(
        "app.services.pix.verify_mp_signature", return_value=True
    ), patch(
        "app.services.pix.fetch_mp_payment",
        return_value={"id": "123456789", "status": "approved"},
    ):
        result = process_webhook(
            db,
            payload={
                "type": "payment",
                "action": "payment.updated",
                "data": {"id": "123456789"},
            },
            ip="127.0.0.1",
        )

    assert result["ok"] is True
    assert result.get("duplicate") is False
    assert payment.status == PaymentStatus.approved
    assert freight.status == FreightStatus.pago
    assert payment.driver_payout_recorded_cents == 95_000
    db.commit.assert_called()
