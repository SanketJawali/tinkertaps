import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.users import User


class Operation(str, PyEnum):
    CONVERT = "convert"
    COMPRESS = "compress"


class JobStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    __table_args__ = (
        CheckConstraint(
            """
            (user_id IS NOT NULL AND anonymous_id IS NULL)
            OR
            (user_id IS NULL AND anonymous_id IS NOT NULL)
            """,
            name="ck_jobs_exactly_one_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    anonymous_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    operation: Mapped[Operation] = mapped_column(
        Enum(Operation, name="operation"),
        nullable=False,
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )

    input_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    output_key: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User | None"] = relationship(
        back_populates="jobs",
    )
