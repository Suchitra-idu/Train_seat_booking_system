"""initial schema: trip, booking (with the overlap EXCLUDE), waitlist

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "trip",
        sa.Column("trip_id", sa.String, primary_key=True),
        sa.Column("route_code", sa.String, nullable=False),
        sa.Column("service_date", sa.String, nullable=False),
        sa.Column("stations", postgresql.JSONB, nullable=False),
        sa.Column("seats", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_trip_route_date", "trip", ["route_code", "service_date"])

    op.create_table(
        "booking",
        sa.Column("booking_id", sa.String, primary_key=True),
        sa.Column("reference", sa.String, nullable=False),
        sa.Column("trip_id", sa.String, nullable=False),
        sa.Column("seat_id", sa.String, nullable=True),
        sa.Column("leg", postgresql.INT4RANGE, nullable=False),
        sa.Column("passenger_id", sa.String, nullable=False),
        sa.Column("travel_class", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("held_until", sa.Integer, nullable=False),
        sa.Column("created_at", sa.Integer, nullable=False),
    )
    op.create_index("ix_booking_reference", "booking", ["reference"])
    op.create_index("ix_booking_trip", "booking", ["trip_id"])
    op.create_index("ix_booking_passenger", "booking", ["passenger_id"])
    op.create_index("ix_booking_status", "booking", ["status"])
    # The one invariant (D2): no two active holds share a trip+seat over overlapping legs.
    op.execute(
        "ALTER TABLE booking ADD CONSTRAINT booking_no_overlap "
        "EXCLUDE USING gist (trip_id WITH =, seat_id WITH =, leg WITH &&) "
        "WHERE (status IN ('HELD','CONFIRMED'))"
    )

    op.create_table(
        "waitlist",
        sa.Column("waitlist_id", sa.String, primary_key=True),
        sa.Column("trip_id", sa.String, nullable=False),
        sa.Column("leg", postgresql.INT4RANGE, nullable=False),
        sa.Column("passenger_id", sa.String, nullable=False),
        sa.Column("travel_class", sa.String, nullable=False),
        sa.Column("created_at", sa.Integer, nullable=False),
    )
    op.create_index("ix_waitlist_trip", "waitlist", ["trip_id"])


def downgrade() -> None:
    op.drop_table("waitlist")
    op.drop_table("booking")
    op.drop_table("trip")
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
