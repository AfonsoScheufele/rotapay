
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.freight import FreightAssign, FreightCreate, FreightPublic, PaymentPublic
from app.services import freight as freight_svc
from app.services import pix as pix_svc

router = APIRouter(prefix="/api/freights", tags=["freights"])

@router.get("", response_model=list[FreightPublic])
def list_freights(db: DbSession, user: CurrentUser) -> list[FreightPublic]:
    items = freight_svc.list_freights(db, user)
    return [freight_svc.to_public(f) for f in items]

@router.post("", response_model=FreightPublic)
def create_freight(
    payload: FreightCreate,
    db: DbSession,
    user: User = Depends(require_roles(UserRole.embarcador, UserRole.admin)),
) -> FreightPublic:
    freight = freight_svc.create_freight(db, user, payload)
    return freight_svc.to_public(freight)

@router.get("/{freight_id}", response_model=FreightPublic)
def get_freight(
    freight_id: UUID, db: DbSession, user: CurrentUser
) -> FreightPublic:
    freight = freight_svc.get_freight_or_404(db, freight_id)
    freight_svc.assert_can_view(user, freight)
    return freight_svc.to_public(freight)

@router.patch("/{freight_id}/assign", response_model=FreightPublic)
def assign_driver(
    freight_id: UUID,
    payload: FreightAssign,
    db: DbSession,
    user: User = Depends(require_roles(UserRole.admin)),
) -> FreightPublic:
    freight = freight_svc.assign_driver(db, user, freight_id, payload.driver_id)
    return freight_svc.to_public(freight)

@router.post("/{freight_id}/accept", response_model=FreightPublic)
def accept_freight(
    freight_id: UUID,
    db: DbSession,
    user: User = Depends(require_roles(UserRole.motorista)),
) -> FreightPublic:
    freight = freight_svc.accept_freight(db, user, freight_id)
    return freight_svc.to_public(freight)

@router.post("/{freight_id}/start", response_model=FreightPublic)
def start_freight(
    freight_id: UUID,
    db: DbSession,
    user: User = Depends(require_roles(UserRole.motorista)),
) -> FreightPublic:
    freight = freight_svc.start_transit(db, user, freight_id)
    return freight_svc.to_public(freight)

@router.post("/{freight_id}/deliver", response_model=FreightPublic)
def deliver_freight(
    freight_id: UUID,
    db: DbSession,
    user: User = Depends(require_roles(UserRole.motorista)),
) -> FreightPublic:
    freight = freight_svc.deliver_freight(db, user, freight_id)
    return freight_svc.to_public(freight)

@router.post("/{freight_id}/cancel", response_model=FreightPublic)
def cancel_freight(
    freight_id: UUID,
    db: DbSession,
    user: User = Depends(require_roles(UserRole.embarcador, UserRole.admin)),
) -> FreightPublic:
    freight = freight_svc.cancel_freight(db, user, freight_id)
    return freight_svc.to_public(freight)

@router.post("/{freight_id}/pix", response_model=PaymentPublic)
def create_pix(
    freight_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PaymentPublic:
    payment = pix_svc.create_pix_charge(db, user, freight_id)
    return PaymentPublic.model_validate(payment)
