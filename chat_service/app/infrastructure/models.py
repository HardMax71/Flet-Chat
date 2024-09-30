# app/infrastructure/models.py
from app.domain.entities import (User as UserEntity, Chat as ChatEntity,
                                 Message as MessageEntity, Token as TokenEntity,
                                 MessageStatus as MessageStatusEntity)
from app.infrastructure.database import Base
from sqlalchemy import Column, Boolean, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

chat_members = Table(
    'chat_members',
    Base.metadata,
    Column('chat_id', Integer, ForeignKey('chats.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)


class User(Base, UserEntity):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    chats = relationship("Chat", secondary=chat_members, back_populates="members", lazy="selectin")
    messages = relationship("Message", back_populates="user", lazy="selectin")
    tokens = relationship("Token", back_populates="user", lazy="selectin")
    message_statuses = relationship("MessageStatus", back_populates="user", lazy="selectin")


class Chat(Base, ChatEntity):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("User", secondary=chat_members, back_populates="chats", lazy="selectin")
    messages = relationship("Message", back_populates="chat", lazy="selectin")


class Message(Base, MessageEntity):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    chat = relationship("Chat", back_populates="messages", lazy="selectin")
    user = relationship("User", back_populates="messages", lazy="selectin")
    statuses = relationship("MessageStatus", back_populates="message", lazy="selectin")


class Token(Base, TokenEntity):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String, unique=True, index=True)
    refresh_token = Column(String, unique=True, index=True)
    token_type = Column(String)
    expires_at = Column(DateTime(timezone=True))
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="tokens", lazy="selectin")


class MessageStatus(Base, MessageStatusEntity):
    __tablename__ = "message_statuses"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    message = relationship("Message", back_populates="statuses", lazy="selectin")
    user = relationship("User", back_populates="message_statuses", lazy="selectin")
