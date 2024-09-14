from abc import ABC, abstractmethod

from app.domain.interfaces import (AbstractUserRepository, AbstractChatRepository,
                                   AbstractMessageRepository, AbstractTokenRepository)
from app.infrastructure.repositories import (SQLAlchemyUserRepository, SQLAlchemyChatRepository,
                                             SQLAlchemyMessageRepository, SQLAlchemyTokenRepository)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class AbstractUnitOfWork(ABC):
    users: AbstractUserRepository
    chats: AbstractChatRepository
    messages: AbstractMessageRepository
    tokens: AbstractTokenRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError


class UnitOfWork(AbstractUnitOfWork):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        self.users = SQLAlchemyUserRepository(self.session)
        self.chats = SQLAlchemyChatRepository(self.session)
        self.messages = SQLAlchemyMessageRepository(self.session)
        self.tokens = SQLAlchemyTokenRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
