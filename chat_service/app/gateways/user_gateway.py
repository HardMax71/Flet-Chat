# app/gateways/user_gateway.py
from typing import List, Optional

from app.domain import models, schemas
from app.infrastructure.security import SecurityService
from app.infrastructure.uow import UnitOfWork, UoWModel


class UserGateway:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_user(self, user_id: int) -> Optional[UoWModel]:
        user = await self.uow.mappers[models.User].get_by_id(user_id)
        return UoWModel(user, self.uow) if user else None

    async def get_by_username(self, username: str) -> Optional[UoWModel]:
        user = await self.uow.mappers[models.User].get_by_username(username)
        return UoWModel(user, self.uow) if user else None

    async def get_all(self, skip: int = 0, limit: int = 100, username: Optional[str] = None) -> List[UoWModel]:
        users = await self.uow.mappers[models.User].get_all(skip, limit, username)
        return [UoWModel(user, self.uow) for user in users]

    async def create_user(self, user: schemas.UserCreate, security_service: SecurityService) -> UoWModel:
        hashed_password = security_service.get_password_hash(user.password)
        db_user = models.User(**user.model_dump(exclude={'password'}), hashed_password=hashed_password)
        return self.uow.register_new(db_user)

    async def search_users(self, query: str, current_user_id: int) -> List[UoWModel]:
        users = await self.uow.mappers[models.User].search_users(query, current_user_id)
        return [UoWModel(user, self.uow) for user in users]

    async def verify_password(self, user: UoWModel, password: str, security_service: SecurityService) -> bool:
        return security_service.verify_password(password, user._model.hashed_password)

    async def update_password(self, user: UoWModel, new_password: str, security_service: SecurityService) -> None:
        hashed_password = security_service.get_password_hash(new_password)
        user._model.hashed_password = hashed_password
        self.uow.register_dirty(user._model)
