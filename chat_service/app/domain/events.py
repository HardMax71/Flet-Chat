# app/domain/events.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    pass


@dataclass
class MessageCreated(Event):
    message_id: int
    chat_id: int
    user_id: int
    content: str
    created_at: datetime
    user: dict
    is_deleted: bool

@dataclass
class MessageUpdated(Event):
    message_id: int
    chat_id: int
    user_id: int
    content: str
    created_at: datetime
    updated_at: datetime
    user: dict
    is_deleted: bool


@dataclass
class MessageDeleted(Event):
    message_id: int
    chat_id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    user: dict
    is_deleted: bool


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
