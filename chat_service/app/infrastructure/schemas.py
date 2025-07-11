# app/infrastructure/schemas.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserBasic(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8)
    username: str | None = None
    is_active: bool | None = None  # sort of soft deleting


class User(UserBase):
    id: int
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ChatBase(BaseModel):
    name: str


class ChatCreate(ChatBase):
    member_ids: list[int]


class ChatUpdate(BaseModel):
    name: str | None = None
    member_ids: list[int] | None = None


class Chat(ChatBase):
    id: int
    created_at: datetime
    members: list[User] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    chat_id: int


class MessageUpdate(BaseModel):
    content: str


class MessageStatus(BaseModel):
    user_id: int
    is_read: bool
    read_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageStatusUpdate(BaseModel):
    is_read: bool = True


class Message(MessageBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    is_deleted: bool
    chat_id: int
    user_id: int
    user: UserBasic
    statuses: list[MessageStatus] = []

    model_config = ConfigDict(from_attributes=True)


class TokenBase(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenCreate(TokenBase):
    expires_at: datetime
    user_id: int


class TokenUpdate(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None


class Token(TokenBase):
    id: int
    expires_at: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class TokenData(BaseModel):
    username: str | None = None
    exp: int | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime
    user_id: int


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
