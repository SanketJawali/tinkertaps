import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.jobs import Job


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            """
            (clerk_user_id IS NOT NULL AND anonymous_id IS NULL)
            OR
            (clerk_user_id IS NULL AND anonymous_id IS NOT NULL)
            """,
            name="exactly_one_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    clerk_user_id: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        nullable=True,
        index=True,
    )

    anonymous_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=True,
        index=True,
    )

    credits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    jobs: Mapped[list["Job"]] = relationship(
        back_populates="user",
    )
