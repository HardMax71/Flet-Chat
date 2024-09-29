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

    async def create_token(self, token: schemas.TokenCreate) -> UoWModel:
        # Check if a token already exists for this user
        existing_token = await self.get_by_user_id(token.user_id)
        if existing_token:
            # Update the existing token directly
            existing_token._model.access_token = token.access_token
            existing_token._model.refresh_token = token.refresh_token
            existing_token._model.expires_at = token.expires_at
            self.uow.register_dirty(existing_token)
        else:
            # Create a new token
            db_token = models.Token(**token.model_dump())
            existing_token = self.uow.register_new(db_token)
        await self.uow.commit()
        return existing_token

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

    async def invalidate_refresh_token(self, refresh_token: str) -> bool:
        token: Optional[UoWModel] = await self.get_by_refresh_token(refresh_token)
        if token:
            # Invalidate the refresh token
            token.refresh_token = None
            self.uow.register_dirty(token)
            await self.uow.commit()
            return True
        return False

    async def delete_token_by_access_token(self, access_token: str) -> bool:
        token: Optional[UoWModel] = await self.get_by_access_token(access_token)
        if token:
            self.uow.register_deleted(token)
            await self.uow.commit()
            return True
        return False

    async def delete_token_by_refresh_token(self, refresh_token: str) -> bool:
        token: Optional[UoWModel] = await self.get_by_refresh_token(refresh_token)
        if token:
            self.uow.register_deleted(token)
            await self.uow.commit()
            return True
        return False
