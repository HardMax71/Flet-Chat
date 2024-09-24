# app/interactors/token_interactor.py
from typing import Optional
from app.domain import schemas
from app.gateways.token_gateway import TokenGateway
from app.infrastructure.uow import UnitOfWork

class TokenInteractor:
    def __init__(self, uow: UnitOfWork, token_gateway: TokenGateway):
        self.uow = uow
        self.token_gateway = token_gateway

    async def create_token(self, token: schemas.TokenCreate) -> schemas.Token:
        new_token = await self.token_gateway.create_token(token)
        await self.uow.commit()
        return schemas.Token.model_validate(new_token)

    async def create_or_update_token(self, token: schemas.TokenCreate) -> schemas.Token:
        existing_token = await self.token_gateway.get_by_user_id(token.user_id)
        if existing_token:
            for key, value in token.model_dump().items():
                setattr(existing_token, key, value)
            updated_token = await self.token_gateway.update_token(existing_token)
            await self.uow.commit()
            return schemas.Token.model_validate(updated_token)
        else:
            new_token = await self.token_gateway.create_token(token)
            await self.uow.commit()
            return schemas.Token.model_validate(new_token)

    async def get_token_by_user_id(self, user_id: int) -> Optional[schemas.Token]:
        token = await self.token_gateway.get_by_user_id(user_id)
        return schemas.Token.model_validate(token) if token else None

    async def get_token_by_access_token(self, access_token: str) -> Optional[schemas.Token]:
        token = await self.token_gateway.get_by_access_token(access_token)
        return schemas.Token.model_validate(token) if token else None

    async def get_token_by_refresh_token(self, refresh_token: str) -> Optional[schemas.Token]:
        token = await self.token_gateway.get_by_refresh_token(refresh_token)
        return schemas.Token.model_validate(token) if token else None

    async def update_token(self, token: schemas.Token) -> Optional[schemas.Token]:
        existing_token = await self.token_gateway.get_by_user_id(token.user_id)
        if not existing_token:
            return None
        for key, value in token.model_dump().items():
            setattr(existing_token, key, value)
        await self.token_gateway.update_token(existing_token)  # Pass the underlying model
        await self.uow.commit()
        return schemas.Token.model_validate(existing_token)

    async def delete_token(self, token_id: int) -> bool:
        token = await self.token_gateway.get_by_user_id(token_id)
        if not token:
            return False
        self.uow.register_deleted(token)
        await self.uow.commit()
        return True

    async def delete_token_by_access_token(self, access_token: str) -> bool:
        token = await self.token_gateway.get_by_access_token(access_token)
        if not token:
            return False
        self.uow.register_deleted(token)
        await self.uow.commit()
        return True
