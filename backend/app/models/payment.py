
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentStatus

class Payment(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("mp_payment_id", name="uq_payments_mp_payment_id"),
    )

    freight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("freights.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=True),
        nullable=False,
        default=PaymentStatus.pending,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    mp_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    qr_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_code_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_paste: Mapped[str | None] = mapped_column(Text, nullable=True)
    driver_payout_recorded_cents: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    freight = relationship("Freight", back_populates="payments")
