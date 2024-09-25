# app/infrastructure/data_mappers.py

from typing import Protocol, TypeVar

from app.domain import models
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar('ModelT')


class DataMapper(Protocol[ModelT]):
    async def insert(self, model: ModelT):
        raise NotImplementedError

    async def delete(self, model: ModelT):
        raise NotImplementedError

    async def update(self, model: ModelT):
        raise NotImplementedError


class UserMapper(DataMapper[models.User]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, model: models.User):
        self.session.add(model)
        await self.session.flush()

    async def delete(self, model: models.User):
        await self.session.delete(model)

    async def update(self, model: models.User):
        await self.session.merge(model)


class ChatMapper(DataMapper[models.Chat]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, model: models.Chat):
        self.session.add(model)
        await self.session.flush()

    async def delete(self, model: models.Chat):
        await self.session.delete(model)

    async def update(self, model: models.Chat):
        await self.session.merge(model)


class MessageMapper(DataMapper[models.Message]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, model: models.Message):
        self.session.add(model)
        await self.session.flush()

    async def delete(self, model: models.Message):
        await self.session.delete(model)

    async def update(self, model: models.Message):
        await self.session.merge(model)


class TokenMapper(DataMapper[models.Token]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, model: models.Token):
        self.session.add(model)
        await self.session.flush()

    async def delete(self, model: models.Token):
        await self.session.delete(model)

    async def update(self, model: models.Token):
        await self.session.merge(model)
