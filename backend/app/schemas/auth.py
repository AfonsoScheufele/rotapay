
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    role: UserRole
    document_masked: str
    created_at: datetime

    model_config = {"from_attributes": True}
