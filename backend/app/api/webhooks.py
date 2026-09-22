
from typing import Any

from fastapi import APIRouter, Header, Request

from app.core.deps import DbSession
from app.services import pix as pix_svc

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.post("/mercadopago")
async def mercadopago_webhook(
    request: Request,
    db: DbSession,
    x_signature: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    query = dict(request.query_params)
    if "data.id" in query and "data" not in payload:
        payload = {
            "type": query.get("type", "payment"),
            "action": "payment.updated",
            "data": {"id": query["data.id"]},
        }

    client_ip = request.client.host if request.client else "unknown"
    return pix_svc.process_webhook(
        db,
        payload=payload,
        ip=client_ip,
        x_signature=x_signature,
        x_request_id=x_request_id,
    )
