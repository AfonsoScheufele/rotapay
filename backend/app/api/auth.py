
from fastapi import APIRouter, HTTPException, Response, status

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, UserPublic

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=UserPublic)
def login(payload: LoginRequest, db: DbSession, response: Response) -> User:
    user = (
        db.query(User)
        .filter(User.email == payload.email.lower(), User.deleted_at.is_(None))
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )

    settings = get_settings()
    token = create_access_token(subject=user.id, role=user.role.value)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,                          
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    return user

@router.post("/logout")
def logout(response: Response) -> dict:
    settings = get_settings()
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        samesite=settings.cookie_samesite,                          
        secure=settings.cookie_secure,
    )
    return {"ok": True}

@router.get("/me", response_model=UserPublic)
def me(user: CurrentUser) -> User:
    return user
