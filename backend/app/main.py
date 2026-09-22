from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import text

from app.api import admin_webhooks, auth, dashboard, freights, webhooks
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal

setup_logging()
settings = get_settings()

app = FastAPI(
    title="RotaPay API",
    description="TMS lite: frete + papéis + mapa + Pix (sandbox Mercado Pago)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(freights.router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)
app.include_router(admin_webhooks.router)


def _check_postgres() -> dict:
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ok"}
        finally:
            db.close()
    except Exception as exc:
        return {"status": "fail", "error": type(exc).__name__}


def _check_redis() -> dict:
    try:
        client = Redis.from_url(settings.redis_url)
        client.ping()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "fail", "error": type(exc).__name__}


@app.get("/api/health")
def health() -> dict:
    components = {
        "app": {"status": "ok"},
        "postgres": _check_postgres(),
        "redis": _check_redis(),
    }
    pg = components["postgres"]["status"]
    rd = components["redis"]["status"]
    if pg == "ok" and rd == "ok":
        overall = "ok"
    elif pg == "fail" and rd == "fail":
        overall = "fail"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "service": "rotapay",
        "components": components,
    }
