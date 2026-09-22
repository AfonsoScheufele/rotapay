"""001_initial"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM(
    "admin", "embarcador", "motorista", name="user_role", create_type=False
)
freight_status = postgresql.ENUM(
    "cotado",
    "aceito",
    "em_transito",
    "entregue",
    "pago",
    "cancelado",
    name="freight_status",
    create_type=False,
)
payment_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "cancelled",
    name="payment_status",
    create_type=False,
)


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    freight_status.create(op.get_bind(), checkfirst=True)
    payment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("document_masked", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "freights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipper_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=True),
        sa.Column("status", freight_status, nullable=False),
        sa.Column("origin_cep", sa.String(length=8), nullable=False),
        sa.Column("origin_address", sa.Text(), nullable=False),
        sa.Column("origin_lat", sa.Float(), nullable=False),
        sa.Column("origin_lng", sa.Float(), nullable=False),
        sa.Column("dest_cep", sa.String(length=8), nullable=False),
        sa.Column("dest_address", sa.Text(), nullable=False),
        sa.Column("dest_lat", sa.Float(), nullable=False),
        sa.Column("dest_lng", sa.Float(), nullable=False),
        sa.Column("weight_grams", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("platform_fee_cents", sa.Integer(), nullable=False),
        sa.Column("driver_net_cents", sa.Integer(), nullable=False),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["driver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["shipper_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_freights_shipper_id", "freights", ["shipper_id"])
    op.create_index("ix_freights_driver_id", "freights", ["driver_id"])
    op.create_index("ix_freights_status", "freights", ["status"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("freight_id", sa.Uuid(), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("mp_payment_id", sa.String(length=64), nullable=True),
        sa.Column("qr_code", sa.Text(), nullable=True),
        sa.Column("qr_code_base64", sa.Text(), nullable=True),
        sa.Column("copy_paste", sa.Text(), nullable=True),
        sa.Column("driver_payout_recorded_cents", sa.Integer(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["freight_id"], ["freights.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mp_payment_id", name="uq_payments_mp_payment_id"),
    )
    op.create_index("ix_payments_freight_id", "payments", ["freight_id"])

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=255), nullable=False),
        sa.Column("mp_payment_id", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_webhook_events_event_key"),
    )
    op.create_index(
        "ix_webhook_events_mp_payment_id", "webhook_events", ["mp_payment_id"]
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("freight_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["freight_id"], ["freights.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_freight_id", "audit_logs", ["freight_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("webhook_events")
    op.drop_table("payments")
    op.drop_table("freights")
    op.drop_table("users")
    payment_status.drop(op.get_bind(), checkfirst=True)
    freight_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
