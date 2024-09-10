# app/domain/schemas.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


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
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    username: Optional[str] = None


class User(UserBase):
    id: int
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ChatBase(BaseModel):
    name: str


class ChatCreate(ChatBase):
    member_ids: List[int]


class ChatUpdate(BaseModel):
    name: Optional[str] = None
    member_ids: Optional[List[int]] = None


class Chat(ChatBase):
    id: int
    created_at: datetime
    members: List[User] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    chat_id: int


class MessageUpdate(BaseModel):
    content: str


class Message(MessageBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool
    chat_id: int
    user_id: int
    user: UserBasic

    model_config = ConfigDict(from_attributes=True)


class TokenBase(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenCreate(TokenBase):
    expires_at: datetime
    user_id: int


class TokenUpdate(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None


class Token(TokenBase):
    id: int
    expires_at: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class TokenData(BaseModel):
    username: Optional[str] = None
    exp: Optional[int] = None


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
