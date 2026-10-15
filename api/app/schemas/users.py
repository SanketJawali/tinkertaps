import uuid
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserBase(BaseModel):
    clerk_user_id: str | None = None
    anonymous_id: uuid.UUID | None = None
    credits: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_exactly_one_identity(self) -> Self:
        has_clerk = self.clerk_user_id is not None
        has_anonymous = self.anonymous_id is not None
        if has_clerk == has_anonymous:
            raise ValueError("Exactly one of clerk_user_id or anonymous_id must be set")
        return self


class UserCreate(UserBase):
    pass


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clerk_user_id: str | None
    anonymous_id: uuid.UUID | None
    credits: int
