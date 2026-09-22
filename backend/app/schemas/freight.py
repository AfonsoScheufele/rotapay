
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import FreightStatus, PaymentStatus
from app.schemas.auth import UserPublic

def _only_digits(value: str) -> str:
    return "".join(c for c in value if c.isdigit())

class FreightCreate(BaseModel):
    origin_cep: str = Field(min_length=8, max_length=9)
    dest_cep: str = Field(min_length=8, max_length=9)
    weight_grams: int = Field(gt=0)
    amount_cents: int = Field(gt=0)

    @field_validator("origin_cep", "dest_cep", mode="before")
    @classmethod
    def normalize_cep(cls, v: str) -> str:
        digits = _only_digits(str(v))
        if len(digits) != 8:
            raise ValueError("CEP deve ter 8 dígitos")
        return digits

class FreightAssign(BaseModel):
    driver_id: UUID

class PaymentPublic(BaseModel):
    id: UUID
    freight_id: UUID
    status: PaymentStatus
    amount_cents: int
    mp_payment_id: str | None
    qr_code: str | None
    qr_code_base64: str | None
    copy_paste: str | None
    driver_payout_recorded_cents: int | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

class FreightPublic(BaseModel):
    id: UUID
    shipper_id: UUID
    driver_id: UUID | None
    status: FreightStatus
    origin_cep: str
    origin_address: str
    origin_lat: float
    origin_lng: float
    dest_cep: str
    dest_address: str
    dest_lat: float
    dest_lng: float
    weight_grams: int
    amount_cents: int
    platform_fee_cents: int
    driver_net_cents: int
    sla_deadline: datetime | None
    created_at: datetime
    updated_at: datetime
    shipper: UserPublic | None = None
    driver: UserPublic | None = None
    latest_payment: PaymentPublic | None = None
    distance_km: float | None = None

    model_config = {"from_attributes": True}

class DashboardFreightItem(BaseModel):
    id: UUID
    status: FreightStatus
    origin_cep: str
    dest_cep: str
    amount_cents: int
    sla_deadline: datetime | None
    sla_state: str

class DashboardSummary(BaseModel):
    fretes_ativos: int
    fretes_sla_atrasado: int
    fretes_sla_no_prazo: int
    fretes_aguardando_sla: int
    receita_bruta_cents: int
    taxas_cents: int
    receita_liquida_cents: int
    por_status: dict[str, int]
    recentes: list[DashboardFreightItem]
    sla_min_hours: int
