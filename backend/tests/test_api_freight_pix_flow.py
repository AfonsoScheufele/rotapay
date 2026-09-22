from fastapi.testclient import TestClient

from app.models.enums import FreightStatus, PaymentStatus, WebhookEventStatus
from app.models.freight import Freight
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent
from tests.conftest import drain_webhook_queue, login


def test_motorista_nao_cria_frete(client: TestClient, seed_users, mock_cep) -> None:
    login(client, seed_users["motorista"].email)
    resp = client.post(
        "/api/freights",
        json={
            "origin_cep": "01310100",
            "dest_cep": "80010000",
            "weight_grams": 10000,
            "amount_cents": 150000,
        },
    )
    assert resp.status_code == 403


def test_transicao_ilegal_retorna_409(
    client: TestClient, seed_users, mock_cep, db
) -> None:
    login(client, seed_users["embarcador"].email)
    created = client.post(
        "/api/freights",
        json={
            "origin_cep": "01310100",
            "dest_cep": "80010000",
            "weight_grams": 10000,
            "amount_cents": 150000,
        },
    )
    assert created.status_code == 200, created.text
    freight_id = created.json()["id"]

    login(client, seed_users["motorista"].email)
    assert client.post(f"/api/freights/{freight_id}/accept").status_code == 200
    bad = client.post(f"/api/freights/{freight_id}/deliver")
    assert bad.status_code == 409


def test_fluxo_frete_pix_webhook_idempotente(
    client: TestClient, seed_users, mock_cep, db
) -> None:
    login(client, seed_users["embarcador"].email)
    created = client.post(
        "/api/freights",
        json={
            "origin_cep": "01310100",
            "dest_cep": "80010000",
            "weight_grams": 25000,
            "amount_cents": 200000,
        },
    )
    assert created.status_code == 200, created.text
    freight_id = created.json()["id"]

    login(client, seed_users["motorista"].email)
    assert client.post(f"/api/freights/{freight_id}/accept").status_code == 200
    assert client.post(f"/api/freights/{freight_id}/start").status_code == 200
    assert client.post(f"/api/freights/{freight_id}/deliver").status_code == 200

    login(client, seed_users["embarcador"].email)
    pix = client.post(f"/api/freights/{freight_id}/pix")
    assert pix.status_code == 200, pix.text
    payment = pix.json()
    assert payment["status"] == PaymentStatus.pending.value
    mp_id = payment["mp_payment_id"]
    assert mp_id.startswith("demo-")

    payload = {
        "type": "payment",
        "action": "payment.updated",
        "data": {"id": mp_id},
    }
    wh1 = client.post("/api/webhooks/mercadopago", json=payload)
    assert wh1.status_code == 200, wh1.text
    body1 = wh1.json()
    assert body1.get("accepted") is True or body1.get("ok") is True
    assert body1.get("duplicate") is not True

    drain_webhook_queue()

    freight = db.get(Freight, freight_id)
    db.refresh(freight)
    assert freight is not None
    assert freight.status == FreightStatus.pago

    pay = (
        db.query(Payment)
        .filter(Payment.mp_payment_id == mp_id, Payment.deleted_at.is_(None))
        .first()
    )
    assert pay is not None
    assert pay.status == PaymentStatus.approved

    wh2 = client.post("/api/webhooks/mercadopago", json=payload)
    assert wh2.status_code == 200
    assert wh2.json().get("duplicate") is True

    drain_webhook_queue()

    db.expire_all()
    freight2 = db.get(Freight, freight_id)
    assert freight2 is not None
    assert freight2.status == FreightStatus.pago

    events = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.mp_payment_id == mp_id)
        .all()
    )
    assert len(events) == 1
    assert events[0].status == WebhookEventStatus.processado


def test_health_tem_componentes(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data
    assert "postgres" in data["components"]
    assert "redis" in data["components"]
    assert data["status"] in ("ok", "degraded", "fail")
