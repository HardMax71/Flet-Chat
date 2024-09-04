# app/infrastructure/unit_of_work.py
from app.infrastructure.repositories import (SQLAlchemyUserRepository, SQLAlchemyChatRepository,
                                             SQLAlchemyMessageRepository, SQLAlchemyTokenRepository)
from sqlalchemy.orm import Session


class UnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.users = SQLAlchemyUserRepository(self.session)
        self.chats = SQLAlchemyChatRepository(self.session)
        self.messages = SQLAlchemyMessageRepository(self.session)
        self.tokens = SQLAlchemyTokenRepository(self.session)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()
