# app/domain/schemas.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserBasic(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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
    members: List[User] = []

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
