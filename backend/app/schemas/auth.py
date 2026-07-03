from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SetupRequest(BaseModel):
    household_name: str = Field(min_length=1, max_length=255)
    owner_email: EmailStr
    owner_display_name: str = Field(min_length=1, max_length=255)
    owner_password: str = Field(min_length=8, max_length=255)


class SetupStatus(BaseModel):
    is_setup: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MemberOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    role: str
    joined_at: datetime


class MeResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    display_name: str
    role: str
    household_id: UUID
    household_name: str


class InviteCreateResponse(BaseModel):
    token: str
    expires_at: datetime


class InviteOut(BaseModel):
    id: UUID
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime


class InviteAcceptRequest(BaseModel):
    token: str
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)
