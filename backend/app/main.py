
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, dashboard, freights, webhooks
from app.core.config import get_settings

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

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "rotapay"}
