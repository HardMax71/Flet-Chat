# app/interactors/token_interactor.py

from app.gateways.interfaces import ITokenGateway
from app.infrastructure import schemas


class TokenInteractor:
    def __init__(self, token_gateway: ITokenGateway):
        self.token_gateway = token_gateway

    async def get_token_by_user_id(self, user_id: int) -> schemas.Token | None:
        token = await self.token_gateway.get_by_user_id(user_id)
        return schemas.Token.model_validate(token._model) if token else None

    async def get_token_by_access_token(
        self, access_token: str
    ) -> schemas.Token | None:
        token = await self.token_gateway.get_by_access_token(access_token)
        return schemas.Token.model_validate(token._model) if token else None

    async def get_token_by_refresh_token(
        self, refresh_token: str
    ) -> schemas.Token | None:
        token = await self.token_gateway.get_by_refresh_token(refresh_token)
        return schemas.Token.model_validate(token._model) if token else None

    async def delete_token_by_access_token(self, access_token: str) -> bool:
        deleted = await self.token_gateway.delete_token_by_access_token(access_token)
        return deleted

    async def delete_token_by_refresh_token(self, refresh_token: str) -> bool:
        return await self.token_gateway.delete_token_by_refresh_token(refresh_token)

    async def invalidate_refresh_token(self, refresh_token: str) -> bool:
        return await self.token_gateway.invalidate_refresh_token(refresh_token)

    async def create_token(
        self, token_create: schemas.TokenCreate
    ) -> schemas.TokenResponse:
        token = await self.token_gateway.create_token(token_create)
        token_dict = {
            "access_token": token._model.access_token,
            "refresh_token": token._model.refresh_token,
            "token_type": token._model.token_type,
            "expires_at": token._model.expires_at,
            "user_id": token._model.user_id,
        }
        return schemas.TokenResponse.model_validate(token_dict)
