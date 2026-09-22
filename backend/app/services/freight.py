
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models.enums import FreightStatus, UserRole
from app.models.freight import Freight
from app.models.payment import Payment
from app.models.user import User
from app.schemas.freight import FreightCreate, FreightPublic, PaymentPublic
from app.services.address import AddressLookupError, lookup_cep
from app.services.audit import write_audit
from app.services.sla import estimate_sla_hours_for_route
from app.services.status_machine import IllegalTransitionError, assert_transition

def calc_fees(amount_cents: int) -> tuple[int, int]:
    settings = get_settings()
    fee = (amount_cents * settings.platform_fee_bps) // 10_000
    net = amount_cents - fee
    return fee, net

def to_public(freight: Freight) -> FreightPublic:
    latest = None
    if freight.payments:
        active = [p for p in freight.payments if p.deleted_at is None]
        active.sort(key=lambda p: p.created_at, reverse=True)
        if active:
            latest = PaymentPublic.model_validate(active[0])

    km, _hours = estimate_sla_hours_for_route(
        freight.origin_lat,
        freight.origin_lng,
        freight.dest_lat,
        freight.dest_lng,
    )
    data = FreightPublic.model_validate(freight)
    data.latest_payment = latest
    data.distance_km = round(km, 1)
    return data

def list_freights(db: Session, user: User) -> list[Freight]:
    q = (
        db.query(Freight)
        .options(
            joinedload(Freight.shipper),
            joinedload(Freight.driver),
            joinedload(Freight.payments),
        )
        .filter(Freight.deleted_at.is_(None))
    )
    if user.role == UserRole.embarcador:
        q = q.filter(Freight.shipper_id == user.id)
    elif user.role == UserRole.motorista:
        q = q.filter(
            (Freight.driver_id == user.id)
            | (
                (Freight.status == FreightStatus.cotado)
                & (Freight.driver_id.is_(None))
            )
        )
    return q.order_by(Freight.created_at.desc()).all()

def get_freight_or_404(db: Session, freight_id: UUID) -> Freight:
    freight = (
        db.query(Freight)
        .options(
            joinedload(Freight.shipper),
            joinedload(Freight.driver),
            joinedload(Freight.payments),
        )
        .filter(Freight.id == freight_id, Freight.deleted_at.is_(None))
        .first()
    )
    if not freight:
        raise HTTPException(status_code=404, detail="Frete não encontrado")
    return freight

def assert_can_view(user: User, freight: Freight) -> None:
    if user.role == UserRole.admin:
        return
    if user.role == UserRole.embarcador and freight.shipper_id == user.id:
        return
    if user.role == UserRole.motorista:
        if freight.driver_id == user.id:
            return
        if freight.status == FreightStatus.cotado and freight.driver_id is None:
            return
    raise HTTPException(status_code=403, detail="Sem acesso a este frete")

def create_freight(db: Session, user: User, payload: FreightCreate) -> Freight:
    if user.role not in (UserRole.embarcador, UserRole.admin):
        raise HTTPException(status_code=403, detail="Apenas embarcador ou admin")

    try:
        origin = lookup_cep(payload.origin_cep)
        dest = lookup_cep(payload.dest_cep)
    except AddressLookupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    fee, net = calc_fees(payload.amount_cents)
    shipper_id = user.id if user.role == UserRole.embarcador else user.id

    freight = Freight(
        shipper_id=shipper_id,
        status=FreightStatus.cotado,
        origin_cep=origin.cep,
        origin_address=origin.address,
        origin_lat=origin.lat,
        origin_lng=origin.lng,
        dest_cep=dest.cep,
        dest_address=dest.address,
        dest_lat=dest.lat,
        dest_lng=dest.lng,
        weight_grams=payload.weight_grams,
        amount_cents=payload.amount_cents,
        platform_fee_cents=fee,
        driver_net_cents=net,
    )
    db.add(freight)
    db.commit()
    db.refresh(freight)
    return get_freight_or_404(db, freight.id)

def _apply_transition(
    db: Session,
    freight: Freight,
    target: FreightStatus,
    *,
    actor: User,
    action: str,
    metadata: dict | None = None,
) -> Freight:
    try:
        assert_transition(freight.status, target)
    except IllegalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    freight.status = target
    if target == FreightStatus.aceito and freight.sla_deadline is None:
        _km, hours = estimate_sla_hours_for_route(
            freight.origin_lat,
            freight.origin_lng,
            freight.dest_lat,
            freight.dest_lng,
        )
        freight.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=hours)

    write_audit(
        db,
        actor_id=actor.id,
        freight_id=freight.id,
        action=action,
        metadata=metadata,
    )
    db.commit()
    return get_freight_or_404(db, freight.id)

def accept_freight(db: Session, user: User, freight_id: UUID) -> Freight:
    if user.role != UserRole.motorista:
        raise HTTPException(status_code=403, detail="Apenas motorista")
    freight = get_freight_or_404(db, freight_id)
    if freight.driver_id is not None:
        raise HTTPException(status_code=409, detail="Frete já possui motorista")
    freight.driver_id = user.id
    return _apply_transition(
        db,
        freight,
        FreightStatus.aceito,
        actor=user,
        action="accept",
        metadata={"driver_id": str(user.id)},
    )

def assign_driver(
    db: Session, user: User, freight_id: UUID, driver_id: UUID
) -> Freight:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Apenas admin")
    freight = get_freight_or_404(db, freight_id)
    driver = (
        db.query(User)
        .filter(
            User.id == driver_id,
            User.role == UserRole.motorista,
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not driver:
        raise HTTPException(status_code=404, detail="Motorista não encontrado")
    freight.driver_id = driver.id
    return _apply_transition(
        db,
        freight,
        FreightStatus.aceito,
        actor=user,
        action="assign",
        metadata={"driver_id": str(driver.id)},
    )

def start_transit(db: Session, user: User, freight_id: UUID) -> Freight:
    freight = get_freight_or_404(db, freight_id)
    if user.role != UserRole.motorista or freight.driver_id != user.id:
        raise HTTPException(status_code=403, detail="Apenas o motorista do frete")
    return _apply_transition(
        db, freight, FreightStatus.em_transito, actor=user, action="start"
    )

def deliver_freight(db: Session, user: User, freight_id: UUID) -> Freight:
    freight = get_freight_or_404(db, freight_id)
    if user.role != UserRole.motorista or freight.driver_id != user.id:
        raise HTTPException(status_code=403, detail="Apenas o motorista do frete")
    return _apply_transition(
        db, freight, FreightStatus.entregue, actor=user, action="deliver"
    )

def cancel_freight(db: Session, user: User, freight_id: UUID) -> Freight:
    freight = get_freight_or_404(db, freight_id)
    if user.role == UserRole.embarcador and freight.shipper_id != user.id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    if user.role == UserRole.motorista:
        raise HTTPException(status_code=403, detail="Motorista não cancela frete")
    if freight.status == FreightStatus.entregue:
        pending = [
            p
            for p in freight.payments
            if p.deleted_at is None and p.status.value == "pending"
        ]
        if pending:
            raise HTTPException(
                status_code=409,
                detail="Não é possível cancelar com Pix pendente após entrega",
            )
    if freight.status in (FreightStatus.pago, FreightStatus.cancelado):
        raise HTTPException(status_code=409, detail="Frete já finalizado")

    return _apply_transition(
        db, freight, FreightStatus.cancelado, actor=user, action="cancel"
    )

def mark_paid_from_webhook(db: Session, freight: Freight) -> Freight:
    assert_transition(freight.status, FreightStatus.pago)
    freight.status = FreightStatus.pago
    return freight
