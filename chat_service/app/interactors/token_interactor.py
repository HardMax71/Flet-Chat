# app/interactors/token_interactor.py
from typing import Optional

from app.gateways.token_gateway import TokenGateway
from app.infrastructure import schemas


class TokenInteractor:
    def __init__(self, token_gateway: TokenGateway):
        self.token_gateway = token_gateway

    async def upsert_token(
            self,
            token: schemas.TokenCreate
    ) -> schemas.Token:
        upserted_token = await self.token_gateway.upsert_token(token)
        return schemas.Token.model_validate(upserted_token._model)

    async def get_token_by_user_id(
            self,
            user_id: int
    ) -> Optional[schemas.Token]:
        token = await self.token_gateway.get_by_user_id(user_id)
        return schemas.Token.model_validate(token._model) if token else None

    async def get_token_by_access_token(
            self,
            access_token: str
    ) -> Optional[schemas.Token]:
        token = await self.token_gateway.get_by_access_token(access_token)
        return schemas.Token.model_validate(token._model) if token else None

    async def get_token_by_refresh_token(
            self,
            refresh_token: str
    ) -> Optional[schemas.Token]:
        token = await self.token_gateway.get_by_refresh_token(refresh_token)
        return schemas.Token.model_validate(token._model) if token else None

    async def delete_token_by_access_token(
            self,
            access_token: str
    ) -> bool:
        deleted = await self.token_gateway.delete_token_by_access_token(access_token)
        return deleted
