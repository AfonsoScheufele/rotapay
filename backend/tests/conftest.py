import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from rq import SimpleWorker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://rotapay:rotapay@localhost:5434/rotapay",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6381/0")
os.environ.setdefault("JWT_SECRET", "test-secret-rotapay-ci")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("MP_ACCESS_TOKEN", "")
os.environ.setdefault("MP_WEBHOOK_SECRET", "")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("COOKIE_SAMESITE", "lax")

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.queue import get_redis_connection
from app.queue.settings import QUEUE_NAME
from app.services.address import AddressResolved

get_settings.cache_clear()


def _ensure_schema() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(text("SELECT 1"))
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def migrate_db() -> None:
    try:
        _ensure_schema()
    except Exception as exc:
        pytest.skip(f"Postgres indisponível para testes de API: {exc}")


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_users(db: Session) -> dict[str, User]:
    emails = {
        "admin": "admin-test@rotapay.com",
        "embarcador": "embarcador-test@rotapay.com",
        "motorista": "motorista-test@rotapay.com",
    }
    users: dict[str, User] = {}
    for key, email in emails.items():
        user = db.query(User).filter(User.email == email).first()
        if not user:
            role = {
                "admin": UserRole.admin,
                "embarcador": UserRole.embarcador,
                "motorista": UserRole.motorista,
            }[key]
            user = User(
                email=email,
                password_hash=hash_password("senha123"),
                role=role,
                name=f"Test {key}",
                document_masked="***.000.000-**",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        users[key] = user
    return users


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str, password: str = "senha123") -> None:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text


def fake_address(cep: str) -> AddressResolved:
    coords = {
        "01310100": (-23.561414, -46.655881, "São Paulo", "SP"),
        "80010000": (-25.428954, -49.267137, "Curitiba", "PR"),
    }
    lat, lng, city, state = coords.get(
        cep, (-23.55, -46.63, "São Paulo", "SP")
    )
    return AddressResolved(
        cep=cep,
        address=f"Rua Teste, {city} - {state}, CEP {cep}",
        lat=lat,
        lng=lng,
        city=city,
        state=state,
    )


@pytest.fixture
def mock_cep():
    with patch("app.services.freight.lookup_cep", side_effect=fake_address):
        yield


def drain_webhook_queue() -> int:
    conn = get_redis_connection()
    worker = SimpleWorker([QUEUE_NAME], connection=conn)
    worker.work(burst=True)
    return 1
