
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import FreightStatus, PaymentStatus, UserRole
from app.models.freight import Freight
from app.models.payment import Payment
from app.models.user import User
from app.schemas.freight import DashboardFreightItem, DashboardSummary

ACTIVE = {
    FreightStatus.cotado,
    FreightStatus.aceito,
    FreightStatus.em_transito,
    FreightStatus.entregue,
}

TRACKED_SLA = {FreightStatus.aceito, FreightStatus.em_transito}

def _sla_state(freight: Freight, now: datetime) -> str:
    if freight.status in (FreightStatus.pago, FreightStatus.cancelado, FreightStatus.entregue):
        return "done"
    if freight.status == FreightStatus.cotado or freight.sla_deadline is None:
        return "pending"
    if freight.sla_deadline < now:
        return "late"
    return "ok"

def dashboard_summary(db: Session, user: User) -> DashboardSummary:
    now = datetime.now(timezone.utc)
    settings = get_settings()

    base = db.query(Freight).filter(Freight.deleted_at.is_(None))
    if user.role == UserRole.embarcador:
        base = base.filter(Freight.shipper_id == user.id)
    elif user.role == UserRole.motorista:
        base = base.filter(
            (Freight.driver_id == user.id)
            | (
                (Freight.status == FreightStatus.cotado)
                & (Freight.driver_id.is_(None))
            )
        )

    freights = base.order_by(Freight.created_at.desc()).all()

    ativos = sum(1 for f in freights if f.status in ACTIVE)
    sla_atrasado = sum(
        1
        for f in freights
        if f.status in TRACKED_SLA
        and f.sla_deadline is not None
        and f.sla_deadline < now
    )
    sla_no_prazo = sum(
        1
        for f in freights
        if f.status in TRACKED_SLA
        and f.sla_deadline is not None
        and f.sla_deadline >= now
    )
    aguardando_sla = sum(
        1 for f in freights if f.status == FreightStatus.cotado
    )

    por_status: dict[str, int] = {s.value: 0 for s in FreightStatus}
    for f in freights:
        por_status[f.status.value] = por_status.get(f.status.value, 0) + 1

    paid_q = (
        db.query(
            func.coalesce(func.sum(Freight.amount_cents), 0),
            func.coalesce(func.sum(Freight.platform_fee_cents), 0),
            func.coalesce(func.sum(Freight.driver_net_cents), 0),
        )
        .join(Payment, Payment.freight_id == Freight.id)
        .filter(
            Freight.deleted_at.is_(None),
            Payment.deleted_at.is_(None),
            Payment.status == PaymentStatus.approved,
            Freight.status == FreightStatus.pago,
        )
    )
    if user.role == UserRole.embarcador:
        paid_q = paid_q.filter(Freight.shipper_id == user.id)
    elif user.role == UserRole.motorista:
        paid_q = paid_q.filter(Freight.driver_id == user.id)

    bruta, taxas, liquida = paid_q.one()

    recentes = [
        DashboardFreightItem(
            id=f.id,
            status=f.status,
            origin_cep=f.origin_cep,
            dest_cep=f.dest_cep,
            amount_cents=f.amount_cents,
            sla_deadline=f.sla_deadline,
            sla_state=_sla_state(f, now),
        )
        for f in freights[:8]
    ]

    return DashboardSummary(
        fretes_ativos=ativos,
        fretes_sla_atrasado=sla_atrasado,
        fretes_sla_no_prazo=sla_no_prazo,
        fretes_aguardando_sla=aguardando_sla,
        receita_bruta_cents=int(bruta),
        taxas_cents=int(taxas),
        receita_liquida_cents=int(liquida),
        por_status=por_status,
        recentes=recentes,
        sla_min_hours=settings.sla_min_hours,
    )
