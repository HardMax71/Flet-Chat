# app/domain/events.py
from datetime import datetime

from pydantic import BaseModel


class Event(BaseModel):
    pass


class UserInfo(BaseModel):
    id: int
    username: str


class MessageEvent(Event):
    message_id: int
    chat_id: int
    user_id: int
    content: str
    created_at: datetime
    user: UserInfo
    is_deleted: bool


class MessageCreated(MessageEvent):
    pass


class MessageUpdated(MessageEvent):
    updated_at: datetime


class MessageDeleted(MessageEvent):
    updated_at: datetime | None = None


class MessageStatusUpdated(Event):
    message_id: int
    chat_id: int
    user_id: int
    is_read: bool
    read_at: datetime | None


class UnreadCountUpdated(Event):
    chat_id: int
    user_id: int
    unread_count: int
