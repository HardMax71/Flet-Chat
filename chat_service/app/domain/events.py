# app/domain/events.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    pass

@dataclass
class UserInfo:
    id: int
    username: str


@dataclass
class MessageEvent(Event):
    message_id: int
    chat_id: int
    user_id: int
    content: str
    created_at: datetime
    user: UserInfo
    is_deleted: bool

@dataclass
class MessageCreated(MessageEvent):
    pass


@dataclass
class MessageUpdated(MessageEvent):
    updated_at: datetime


@dataclass
class MessageDeleted(MessageEvent):
    updated_at: Optional[datetime] = None


@dataclass
class MessageStatusUpdated(Event):
    message_id: int
    chat_id: int
    user_id: int
    is_read: bool
    read_at: Optional[datetime]


@dataclass
class UnreadCountUpdated(Event):
    chat_id: int
    user_id: int
    unread_count: int
