"""move anonymous_id to users, add credits, require job user_id

Revision ID: a1b2c3d4e5f6
Revises: 6f2c18a71b11
Create Date: 2026-07-26 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6f2c18a71b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("anonymous_id", sa.UUID(), nullable=True))
    op.add_column(
        "users",
        sa.Column("credits", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("users", "clerk_user_id", existing_type=sa.String(), nullable=True)
    op.create_index(op.f("ix_users_anonymous_id"), "users", ["anonymous_id"], unique=True)
    op.create_check_constraint(
        "ck_users_exactly_one_identity",
        "users",
        """
        (clerk_user_id IS NOT NULL AND anonymous_id IS NULL)
        OR
        (clerk_user_id IS NULL AND anonymous_id IS NOT NULL)
        """,
    )

    # Create a user row for each distinct anonymous job identity.
    op.execute(
        """
        INSERT INTO users (id, clerk_user_id, anonymous_id, credits)
        SELECT gen_random_uuid(), NULL, j.anonymous_id, 0
        FROM (
            SELECT DISTINCT anonymous_id
            FROM jobs
            WHERE anonymous_id IS NOT NULL
        ) AS j
        """
    )
    op.execute(
        """
        UPDATE jobs AS job
        SET user_id = users.id
        FROM users
        WHERE job.anonymous_id IS NOT NULL
          AND users.anonymous_id = job.anonymous_id
          AND job.user_id IS NULL
        """
    )

    op.drop_constraint(
        op.f("ck_jobs_ck_jobs_exactly_one_identity"),
        "jobs",
        type_="check",
    )
    op.drop_index(op.f("ix_jobs_anonymous_id"), table_name="jobs")
    op.drop_column("jobs", "anonymous_id")
    op.alter_column("jobs", "user_id", existing_type=sa.UUID(), nullable=False)

    # Existing enum labels use member names (PENDING, CONVERT, ...).
    op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'DRAFT'")

    op.alter_column("users", "credits", server_default=None)


def downgrade() -> None:
    op.add_column("jobs", sa.Column("anonymous_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_jobs_anonymous_id"), "jobs", ["anonymous_id"], unique=False)

    op.execute(
        """
        UPDATE jobs AS job
        SET anonymous_id = users.anonymous_id,
            user_id = NULL
        FROM users
        WHERE users.id = job.user_id
          AND users.anonymous_id IS NOT NULL
        """
    )

    op.alter_column("jobs", "user_id", existing_type=sa.UUID(), nullable=True)
    op.create_check_constraint(
        "ck_jobs_exactly_one_identity",
        "jobs",
        """
        (user_id IS NOT NULL AND anonymous_id IS NULL)
        OR
        (user_id IS NULL AND anonymous_id IS NOT NULL)
        """,
    )

    op.drop_constraint("ck_users_exactly_one_identity", "users", type_="check")
    op.drop_index(op.f("ix_users_anonymous_id"), table_name="users")
    op.drop_column("users", "credits")
    op.drop_column("users", "anonymous_id")
    op.alter_column("users", "clerk_user_id", existing_type=sa.String(), nullable=False)
