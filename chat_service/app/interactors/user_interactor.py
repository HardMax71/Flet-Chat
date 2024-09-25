# app/interactors/user_interactor.py
from typing import List, Optional

from app.domain import schemas, models
from app.gateways.user_gateway import UserGateway
from app.infrastructure.security import SecurityService
from app.infrastructure.uow import UnitOfWork, UoWModel


class UserInteractor:
    def __init__(self, uow: UnitOfWork, security_service: SecurityService, user_gateway: UserGateway):
        self.uow = uow
        self.security_service = security_service
        self.user_gateway = user_gateway

    async def get_user(self, user_id: int) -> Optional[schemas.User]:
        user: Optional[UoWModel] = await self.user_gateway.get_user(user_id)
        return schemas.User.model_validate(user._model) if user else None

    async def get_user_by_username(self, username: str) -> Optional[schemas.User]:
        user: Optional[UoWModel] = await self.user_gateway.get_by_username(username)
        return schemas.User.model_validate(user._model) if user else None

    async def get_users(self, skip: int = 0, limit: int = 100, username: Optional[str] = None) -> List[schemas.User]:
        users: List[UoWModel] = await self.user_gateway.get_all(skip, limit, username)
        return [schemas.User.model_validate(user._model) for user in users]

    async def create_user(self, user: schemas.UserCreate) -> schemas.User:
        new_user: models.User = await self.user_gateway.create_user(user, self.security_service)
        await self.uow.commit()
        return schemas.User.model_validate(new_user)

    async def update_user(self, user_id: int, user_update: schemas.UserUpdate) -> Optional[schemas.User]:
        user: Optional[UoWModel] = await self.user_gateway.get_user(user_id)
        if not user:
            return None
        for key, value in user_update.model_dump(exclude_unset=True).items():
            if key == 'password':
                await self.user_gateway.update_password(user, value, self.security_service)
            else:
                setattr(user, key, value)
        await self.uow.commit()
        return schemas.User.model_validate(user._model)

    async def delete_user(self, user_id: int) -> bool:
        user: Optional[UoWModel] = await self.user_gateway.get_user(user_id)
        if not user:
            return False
        self.uow.register_deleted(user._model)
        await self.uow.commit()
        return True

    async def search_users(self, query: str, current_user_id: int) -> List[schemas.User]:
        users: List[UoWModel] = await self.user_gateway.search_users(query, current_user_id)
        return [schemas.User.model_validate(user._model) for user in users]

    async def verify_user_password(self, username: str, password: str) -> Optional[schemas.User]:
        user: Optional[UoWModel] = await self.user_gateway.get_by_username(username)
        if not user:
            return None
        if await self.user_gateway.verify_password(user, password, self.security_service):
            return schemas.User.model_validate(user._model)
        return None
