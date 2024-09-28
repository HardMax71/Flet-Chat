# app/infrastructure/token_gateway.py
from typing import Optional

from app.domain import models
from app.gateways.interfaces import ITokenGateway
from app.infrastructure import schemas
from app.infrastructure.data_mappers import TokenMapper
from app.infrastructure.uow import UnitOfWork, UoWModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TokenGateway(ITokenGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        uow.mappers[models.Token] = TokenMapper(session)

    async def upsert_token(self, token: schemas.TokenCreate) -> UoWModel:
        stmt = select(models.Token).filter(models.Token.user_id == token.user_id)
        result = await self.session.execute(stmt)
        existing_token = result.scalar_one_or_none()

        if existing_token:
            for key, value in token.model_dump().items():
                setattr(existing_token, key, value)
            self.uow.register_dirty(existing_token)
            uow_token = UoWModel(existing_token, self.uow)
        else:
            new_token = models.Token(**token.model_dump())
            uow_token = self.uow.register_new(new_token)

        await self.uow.commit()
        return uow_token

    async def get_by_user_id(self, user_id: int) -> Optional[UoWModel]:
        stmt = select(models.Token).filter(models.Token.user_id == user_id)
        result = await self.session.execute(stmt)
        token = result.scalar_one_or_none()
        return UoWModel(token, self.uow) if token else None

    async def get_by_access_token(self, access_token: str) -> Optional[UoWModel]:
        stmt = select(models.Token).filter(models.Token.access_token == access_token)
        result = await self.session.execute(stmt)
        token = result.scalar_one_or_none()
        return UoWModel(token, self.uow) if token else None

    async def get_by_refresh_token(self, refresh_token: str) -> Optional[UoWModel]:
        stmt = select(models.Token).filter(models.Token.refresh_token == refresh_token)
        result = await self.session.execute(stmt)
        token = result.scalar_one_or_none()
        return UoWModel(token, self.uow) if token else None

    async def delete_token_by_access_token(self, access_token: str) -> bool:
        token = await self.get_by_access_token(access_token)
        if token:
            self.uow.register_deleted(token._model)
            await self.uow.commit()
            return True
        return False
