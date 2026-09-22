"""002_webhook_queue"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_webhook_queue"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "webhook_events",
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="recebido",
        ),
    )
    op.add_column(
        "webhook_events",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("webhook_events", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "webhook_events",
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.alter_column(
        "webhook_events",
        "processed_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )
    op.execute("UPDATE webhook_events SET processed_at = NULL WHERE status = 'recebido'")
    op.create_index("ix_webhook_events_status", "webhook_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_webhook_events_status", table_name="webhook_events")
    op.execute(
        "UPDATE webhook_events SET processed_at = COALESCE(processed_at, created_at)"
    )
    op.alter_column(
        "webhook_events",
        "processed_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    op.drop_column("webhook_events", "updated_at")
    op.drop_column("webhook_events", "raw_payload")
    op.drop_column("webhook_events", "last_error")
    op.drop_column("webhook_events", "attempts")
    op.drop_column("webhook_events", "status")
