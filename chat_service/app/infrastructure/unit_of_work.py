# app/infrastructure/unit_of_work.py
from abc import ABC, abstractmethod

from app.domain.interfaces import (
    AbstractUserRepository,
    AbstractChatRepository,
    AbstractMessageRepository,
    AbstractTokenRepository,
)
from app.infrastructure.repositories import (
    SQLAlchemyUserRepository,
    SQLAlchemyChatRepository,
    SQLAlchemyMessageRepository,
    SQLAlchemyTokenRepository,
)
from app.infrastructure.security import SecurityService
from app.config import AppConfig
from sqlalchemy.ext.asyncio import AsyncSession


class AbstractUnitOfWork(ABC):
    users: AbstractUserRepository
    chats: AbstractChatRepository
    messages: AbstractMessageRepository
    tokens: AbstractTokenRepository

    async def __aenter__(self):
        raise NotImplementedError

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    @abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError


class UnitOfWork(AbstractUnitOfWork):
    def __init__(self, session: AsyncSession, config: AppConfig):
        self.session = session
        self.config = config

    async def __aenter__(self):
        security_service = SecurityService(self.config)
        self.users = SQLAlchemyUserRepository(self.session, security_service)
        self.chats = SQLAlchemyChatRepository(self.session)
        self.messages = SQLAlchemyMessageRepository(self.session)
        self.tokens = SQLAlchemyTokenRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
