# app/gateways/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional

from app.infrastructure import schemas
from app.infrastructure.security import SecurityService
from app.infrastructure.uow import UoWModel


class IChatGateway(ABC):
    @abstractmethod
    async def get_chat(self, chat_id: int, user_id: int) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def get_all(
        self, user_id: int, skip: int = 0, limit: int = 100, name: Optional[str] = None
    ) -> List[UoWModel]:
        pass

    @abstractmethod
    async def create_chat(self, chat: schemas.ChatCreate, user_id: int) -> UoWModel:
        pass

    @abstractmethod
    async def add_member(
        self, chat_id: int, user_id: int, current_user_id: int
    ) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def delete_chat(self, chat_id: int, user_id: int) -> None:
        pass

    @abstractmethod
    async def remove_member(
        self, chat_id: int, user_id: int, current_user_id: int
    ) -> bool:
        pass

    @abstractmethod
    async def start_chat(
        self, current_user_id: int, other_user_id: int
    ) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def get_user_ids_in_chat(self, chat_id: int) -> List[int]:
        pass

    @abstractmethod
    async def get_unread_messages_count(self, chat_id: int, user_id: int) -> int:
        pass

    @abstractmethod
    async def get_unread_counts_for_chat_members(
        self, chat_id: int, current_user_id: int
    ) -> dict[int, int]:
        pass


class IMessageGateway(ABC):
    @abstractmethod
    async def get_message(self, message_id: int, user_id: int) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def get_all(
        self,
        chat_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        content: Optional[str] = None,
    ) -> List[UoWModel]:
        pass

    @abstractmethod
    async def create_message(
        self, message: schemas.MessageCreate, user_id: int
    ) -> UoWModel:
        pass

    @abstractmethod
    async def update_message(
        self, message_id: int, message_update: schemas.MessageUpdate, user_id: int
    ) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def delete_message(self, message_id: int, user_id: int) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def update_message_status(
        self, message_id: int, user_id: int, status_update: schemas.MessageStatusUpdate
    ) -> Optional[UoWModel]:
        pass


class ITokenGateway(ABC):
    @abstractmethod
    async def create_token(self, token: schemas.TokenCreate) -> UoWModel:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def get_by_access_token(self, access_token: str) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def get_by_refresh_token(self, refresh_token: str) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def invalidate_refresh_token(self, refresh_token: str) -> bool:
        pass

    @abstractmethod
    async def delete_token_by_access_token(self, access_token: str) -> bool:
        pass

    @abstractmethod
    async def delete_token_by_refresh_token(self, refresh_token: str) -> bool:
        pass


class IUserGateway(ABC):
    @abstractmethod
    async def get_user(self, user_id: int) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def get_all(
        self, skip: int = 0, limit: int = 100, username: Optional[str] = None
    ) -> List[UoWModel]:
        pass

    @abstractmethod
    async def update_user(
        self,
        user: UoWModel,
        user_update: schemas.UserUpdate,
        security_service: SecurityService,
    ) -> UoWModel:
        pass

    @abstractmethod
    async def create_user(
        self, user: schemas.UserCreate, security_service: SecurityService
    ) -> Optional[UoWModel]:
        pass

    @abstractmethod
    async def search_users(self, query: str, current_user_id: int) -> List[UoWModel]:
        pass

    @abstractmethod
    async def verify_password(
        self, user: UoWModel, password: str, security_service: SecurityService
    ) -> bool:
        pass

    @abstractmethod
    async def update_password(
        self, user: UoWModel, new_password: str, security_service: SecurityService
    ) -> None:
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> Optional[UoWModel]:
        pass
