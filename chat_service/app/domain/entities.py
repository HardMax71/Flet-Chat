# app/domain/entities.py
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class User:
    id: int
    username: str
    email: str
    hashed_password: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = True
    chats: list["Chat"] = field(default_factory=list)
    messages: list["Message"] = field(default_factory=list)
    tokens: list["Token"] = field(default_factory=list)
    message_statuses: list["MessageStatus"] = field(default_factory=list)


@dataclass
class Chat:
    id: int
    name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    members: list[User] = field(default_factory=list)
    messages: list["Message"] = field(default_factory=list)


@dataclass
class Message:
    id: int
    content: str
    chat_id: int
    user_id: int
    chat: Chat | None = None
    user: User | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    is_deleted: bool = False
    statuses: list["MessageStatus"] = field(default_factory=list)


@dataclass
class Token:
    id: int
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime
    user_id: int
    user: User | None = None


@dataclass
class MessageStatus:
    id: int
    message_id: int
    user_id: int
    is_read: bool = False
    read_at: datetime | None = None
    message: Message | None = None
    user: User | None = None
