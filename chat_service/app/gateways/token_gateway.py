# app/gateways/token_gateway.py
from typing import Optional
from app.domain import models, schemas
from app.infrastructure.uow import UnitOfWork, UoWModel

class TokenGateway:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_token(self, token: schemas.TokenCreate) -> UoWModel:
        db_token = models.Token(**token.model_dump())
        return self.uow.register_new(db_token)

    async def get_by_user_id(self, user_id: int) -> Optional[UoWModel]:
        token = await self.uow.mappers[models.Token].get_by_user_id(user_id)
        return UoWModel(token, self.uow) if token else None

    async def get_by_access_token(self, access_token: str) -> Optional[UoWModel]:
        token = await self.uow.mappers[models.Token].get_by_access_token(access_token)
        return UoWModel(token, self.uow) if token else None

    async def get_by_refresh_token(self, refresh_token: str) -> Optional[UoWModel]:
        token = await self.uow.mappers[models.Token].get_by_refresh_token(refresh_token)
        return UoWModel(token, self.uow) if token else None

    async def update_token(self, token: models.Token) -> UoWModel:
        await self.uow.mappers[models.Token].update(token)
        return UoWModel(token, self.uow)
