# app/infrastructure/user_gateway.py


from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateways.interfaces import IUserGateway
from app.infrastructure import models, schemas
from app.infrastructure.data_mappers import UserMapper
from app.infrastructure.models import Token
from app.infrastructure.security import SecurityService
from app.infrastructure.uow import UnitOfWork, UoWModel


class UserGateway(IUserGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        uow.mappers[models.User] = UserMapper(session)

    async def get_user(self, user_id: int) -> UoWModel | None:
        stmt = select(models.User).filter(models.User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return UoWModel(user, self.uow) if user else None

    async def get_by_email(self, email: str) -> UoWModel | None:
        stmt = select(models.User).filter(
            func.lower(models.User.email) == func.lower(email)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return UoWModel(user, self.uow) if user else None

    async def get_by_username(self, username: str) -> UoWModel | None:
        stmt = select(models.User).filter(
            func.lower(models.User.username) == func.lower(username)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return UoWModel(user, self.uow) if user else None

    async def get_all(
        self, skip: int = 0, limit: int = 100, username: str | None = None
    ) -> list[UoWModel]:
        stmt = select(models.User)
        if username:
            stmt = stmt.filter(models.User.username.ilike(f"%{username}%"))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        return [UoWModel(user, self.uow) for user in users]

    async def update_user(
        self,
        user: UoWModel,
        user_update: schemas.UserUpdate,
        security_service: SecurityService,
    ) -> UoWModel:
        user_update_data = user_update.model_dump(exclude_unset=True)
        if "password" in user_update_data:
            hashed_password = security_service.get_password_hash(user_update_data["password"])
            user.hashed_password = hashed_password
        if "username" in user_update_data:
            user.username = user_update_data["username"]
        if "email" in user_update_data:
            user.email = user_update_data["email"]
        if "is_active" in user_update_data:
            user.is_active = user_update_data["is_active"]

        await self.uow.commit()
        return user

    async def create_user(
        self, user: schemas.UserCreate, security_service: SecurityService
    ) -> UoWModel | None:
        existing_user = await self.get_by_email(user.email)
        if existing_user:
            return None
        existing_username = await self.get_by_username(user.username)
        if existing_username:
            return None

        hashed_password = security_service.get_password_hash(user.password)
        db_user = models.User(
            **user.model_dump(exclude={"password"}), hashed_password=hashed_password
        )
        uow_user = self.uow.register_new(db_user)
        await self.uow.commit()
        return uow_user

    async def search_users(self, query: str, current_user_id: int) -> list[UoWModel]:
        stmt = select(models.User).filter(
            models.User.id != current_user_id, models.User.username.ilike(f"%{query}%")
        )
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        return [UoWModel(user, self.uow) for user in users]

    async def verify_password(
        self, user: UoWModel, password: str, security_service: SecurityService
    ) -> bool:
        return security_service.verify_password(password, user._model.hashed_password)

    async def update_password(
        self, user: UoWModel, new_password: str, security_service: SecurityService
    ) -> None:
        hashed_password = security_service.get_password_hash(new_password)
        user._model.hashed_password = hashed_password
        self.uow.register_dirty(user._model)
        await self.uow.commit()

    async def delete_user(self, user_id: int) -> UoWModel | None:
        stmt = select(models.User).filter(models.User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Delete user's tokens first to avoid foreign key issues
            token_stmt = select(Token).filter(Token.user_id == user_id)
            token_result = await self.session.execute(token_stmt)
            tokens = token_result.scalars().all()
            for token in tokens:
                self.uow.register_deleted(token)

            uow_user = UoWModel(user, self.uow)
            self.uow.register_deleted(user)
            await self.uow.commit()
            return uow_user
        return None
