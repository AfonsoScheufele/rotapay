
from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import FreightStatus, UserRole
from app.models.freight import Freight
from app.models.user import User
from app.services.freight import calc_fees
from app.services.sla import estimate_sla_hours_for_route

def run_seed() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "admin@rotapay.com").first()
        if existing:
            print("Seed já aplicado.")
            return

        admin = User(
            email="admin@rotapay.com",
            password_hash=hash_password("senha123"),
            role=UserRole.admin,
            name="Admin RotaPay",
            document_masked="***.456.789-**",
        )
        embarcador = User(
            email="embarcador@rotapay.com",
            password_hash=hash_password("senha123"),
            role=UserRole.embarcador,
            name="Transportes Sul Ltda",
            document_masked="12.***.***/0001-**",
        )
        motorista = User(
            email="motorista@rotapay.com",
            password_hash=hash_password("senha123"),
            role=UserRole.motorista,
            name="Carlos Motorista",
            document_masked="***.111.222-**",
        )
        db.add_all([admin, embarcador, motorista])
        db.flush()

        amount = 250_000               
        fee, net = calc_fees(amount)
        frete = Freight(
            shipper_id=embarcador.id,
            driver_id=None,
            status=FreightStatus.cotado,
            origin_cep="01310100",
            origin_address="Avenida Paulista, Bela Vista, São Paulo - SP, CEP 01310100",
            origin_lat=-23.561414,
            origin_lng=-46.655881,
            dest_cep="80010000",
            dest_address="Praça Tiradentes, Centro, Curitiba - PR, CEP 80010000",
            dest_lat=-25.428954,
            dest_lng=-49.267137,
            weight_grams=850_000,
            amount_cents=amount,
            platform_fee_cents=fee,
            driver_net_cents=net,
        )

        amount2 = 180_000
        fee2, net2 = calc_fees(amount2)
        _km2, hours2 = estimate_sla_hours_for_route(
            -25.428954, -49.267137, -23.561414, -46.655881
        )
        frete2 = Freight(
            shipper_id=embarcador.id,
            driver_id=motorista.id,
            status=FreightStatus.em_transito,
            origin_cep="80010000",
            origin_address="Praça Tiradentes, Centro, Curitiba - PR, CEP 80010000",
            origin_lat=-25.428954,
            origin_lng=-49.267137,
            dest_cep="01310100",
            dest_address="Avenida Paulista, Bela Vista, São Paulo - SP, CEP 01310100",
            dest_lat=-23.561414,
            dest_lng=-46.655881,
            weight_grams=420_000,
            amount_cents=amount2,
            platform_fee_cents=fee2,
            driver_net_cents=net2,
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=hours2),
        )

        db.add_all([frete, frete2])
        db.commit()
        print("Seed OK.")
        print("  admin@rotapay.com / senha123")
        print("  embarcador@rotapay.com / senha123")
        print("  motorista@rotapay.com / senha123")
    finally:
        db.close()
