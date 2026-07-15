import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.jobs import Job


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    clerk_user_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    jobs: Mapped[list["Job"]] = relationship(
        back_populates="user",
    )
