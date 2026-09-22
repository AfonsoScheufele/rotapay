
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FreightStatus

class Freight(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "freights"

    shipper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[FreightStatus] = mapped_column(
        Enum(FreightStatus, name="freight_status", native_enum=True),
        nullable=False,
        default=FreightStatus.cotado,
        index=True,
    )

    origin_cep: Mapped[str] = mapped_column(String(8), nullable=False)
    origin_address: Mapped[str] = mapped_column(Text, nullable=False)
    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)

    dest_cep: Mapped[str] = mapped_column(String(8), nullable=False)
    dest_address: Mapped[str] = mapped_column(Text, nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False)

    weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    driver_net_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    sla_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    shipper = relationship(
        "User",
        back_populates="freights_as_shipper",
        foreign_keys=[shipper_id],
    )
    driver = relationship(
        "User",
        back_populates="freights_as_driver",
        foreign_keys=[driver_id],
    )
    payments = relationship("Payment", back_populates="freight")
    audit_logs = relationship("AuditLog", back_populates="freight")
