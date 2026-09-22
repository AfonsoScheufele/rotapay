
from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    document_masked: Mapped[str] = mapped_column(String(32), nullable=False)

    freights_as_shipper = relationship(
        "Freight",
        back_populates="shipper",
        foreign_keys="Freight.shipper_id",
    )
    freights_as_driver = relationship(
        "Freight",
        back_populates="driver",
        foreign_keys="Freight.driver_id",
    )
    audit_logs = relationship("AuditLog", back_populates="actor")
