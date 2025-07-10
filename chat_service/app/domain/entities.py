# app/domain/entities.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class User:
    id: int
    username: str
    email: str
    hashed_password: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    chats: List["Chat"] = field(default_factory=list)
    messages: List["Message"] = field(default_factory=list)
    tokens: List["Token"] = field(default_factory=list)
    message_statuses: List["MessageStatus"] = field(default_factory=list)


@dataclass
class Chat:
    id: int
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    members: List[User] = field(default_factory=list)
    messages: List["Message"] = field(default_factory=list)


@dataclass
class Message:
    id: int
    content: str
    chat_id: int
    user_id: int
    chat: Optional[Chat] = None
    user: Optional[User] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
    statuses: List["MessageStatus"] = field(default_factory=list)


@dataclass
class Token:
    id: int
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime
    user_id: int
    user: Optional[User] = None


@dataclass
class MessageStatus:
    id: int
    message_id: int
    user_id: int
    is_read: bool = False
    read_at: Optional[datetime] = None
    message: Optional[Message] = None
    user: Optional[User] = None
