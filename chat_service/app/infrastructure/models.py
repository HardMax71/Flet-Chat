# app/infrastructure/models.py
from typing import Optional, List
from datetime import datetime

from app.infrastructure.database import Base
from sqlalchemy import Integer, String, DateTime, ForeignKey, Table, Column, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
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
        "Chat", secondary=chat_members, back_populates="members", lazy="selectin"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="user", lazy="selectin"
    )
    tokens: Mapped[List["Token"]] = relationship(
        "Token", back_populates="user", lazy="selectin"
    )
    message_statuses: Mapped[List["MessageStatus"]] = relationship(
        "MessageStatus", back_populates="user", lazy="selectin"
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
        "User", secondary=chat_members, back_populates="chats", lazy="selectin"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="chat", lazy="selectin"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    chat: Mapped[Chat] = relationship(
        "Chat", back_populates="messages", lazy="selectin"
    )
    user: Mapped[User] = relationship(
        "User", back_populates="messages", lazy="selectin"
    )
    statuses: Mapped[List["MessageStatus"]] = relationship(
        "MessageStatus", back_populates="message", lazy="selectin"
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
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    user: Mapped[User] = relationship("User", back_populates="tokens", lazy="selectin")


class MessageStatus(Base):
    __tablename__ = "message_statuses"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    message: Mapped[Message] = relationship(
        "Message", back_populates="statuses", lazy="selectin"
    )
    user: Mapped[User] = relationship(
        "User", back_populates="message_statuses", lazy="selectin"
    )
