
from fastapi import APIRouter, Depends

from app.core.deps import DbSession, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.freight import DashboardSummary
from app.services.dashboard import dashboard_summary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: DbSession,
    user: User = Depends(
        require_roles(UserRole.admin, UserRole.embarcador, UserRole.motorista)
    ),
) -> DashboardSummary:
    return dashboard_summary(db, user)
