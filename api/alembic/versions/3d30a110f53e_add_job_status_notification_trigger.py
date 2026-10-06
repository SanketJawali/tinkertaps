"""add job status notification trigger

Revision ID: 3d30a110f53e
Revises: c8d9e0f1a2b3
Create Date: 2026-10-06 16:01:29.648715

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3d30a110f53e'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_job_status_update()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.status IS DISTINCT FROM NEW.status THEN
                PERFORM pg_notify(
                    'job_status_updates',
                    json_build_object(
                        'job_id', NEW.id,
                        'status', NEW.status
                    )::text
                );
            END IF;

            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER job_status_update_trigger
        AFTER UPDATE OF status ON jobs
        FOR EACH ROW
        EXECUTE FUNCTION notify_job_status_update();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS job_status_update_trigger
        ON jobs;
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS notify_job_status_update();
    """)
