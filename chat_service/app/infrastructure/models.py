# app/infrastructure/models.py
from typing import Optional, List
from datetime import datetime

from app.infrastructure.database import Base
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    Table,
    Column,
    Boolean,
    select,
    Index,
    update,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, selectinload, joinedload
from sqlalchemy.sql import func

chat_members = Table(
    "chat_members",
    Base.metadata,
    Column("chat_id", Integer, ForeignKey("chats.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    chats: Mapped[List["Chat"]] = relationship(
        "Chat", secondary=chat_members, back_populates="members", lazy="select"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="user", lazy="select"
    )
    tokens: Mapped[List["Token"]] = relationship(
        "Token", back_populates="user", lazy="select"
    )
    message_statuses: Mapped[List["MessageStatus"]] = relationship(
        "MessageStatus", back_populates="user", lazy="select"
    )


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    members: Mapped[List[User]] = relationship(
        "User", secondary=chat_members, back_populates="chats", lazy="select"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="chat", lazy="select"
    )


class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        Index("ix_messages_chat_created", "chat_id", "created_at"),
        Index("ix_messages_user_created", "user_id", "created_at"),
        Index("ix_messages_chat_deleted", "chat_id", "is_deleted"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    chat: Mapped[Chat] = relationship(
        "Chat",
        back_populates="messages",
        lazy="joined",  # Many-to-one, often accessed
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="messages",
        lazy="joined",  # Many-to-one, often accessed
    )
    statuses: Mapped[List["MessageStatus"]] = relationship(
        "MessageStatus", back_populates="message", lazy="select"
    )


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    access_token: Mapped[str] = mapped_column(String, unique=True, index=True)
    refresh_token: Mapped[str] = mapped_column(String, unique=True, index=True)
    token_type: Mapped[str] = mapped_column(String)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )

    user: Mapped[User] = relationship("User", back_populates="tokens", lazy="select")


class MessageStatus(Base):
    __tablename__ = "message_statuses"

    __table_args__ = (
        Index("ix_message_status_message_user", "message_id", "user_id"),
        Index("ix_message_status_user_read", "user_id", "is_read"),
        Index("ix_message_status_message_read", "message_id", "is_read"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    message: Mapped[Message] = relationship(
        "Message",
        back_populates="statuses",
        lazy="joined",  # Many-to-one, often accessed
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="message_statuses",
        lazy="joined",  # Many-to-one, often accessed
    )
