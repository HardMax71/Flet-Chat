# app/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain import schemas


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[schemas.User]:
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[schemas.User]:
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100, username: Optional[str] = None) -> List[schemas.User]:
        pass

    @abstractmethod
    async def create(self, user: schemas.UserCreate) -> schemas.User:
        pass

    @abstractmethod
    async def update(self, user_id: int, user_update: schemas.UserUpdate) -> Optional[schemas.User]:
        pass

    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def search_users(self, query: str, current_user_id: int) -> List[schemas.User]:
        pass


class AbstractChatRepository(ABC):
    @abstractmethod
    async def get_by_id(self, chat_id: int, user_id: int) -> Optional[schemas.Chat]:
        pass

    @abstractmethod
    async def get_all(self, user_id: int, skip: int = 0, limit: int = 100, name: Optional[str] = None) -> List[
        schemas.Chat]:
        pass

    @abstractmethod
    async def create(self, chat: schemas.ChatCreate, user_id: int) -> schemas.Chat:
        pass

    @abstractmethod
    async def update(self, chat_id: int, chat_update: schemas.ChatUpdate) -> Optional[schemas.Chat]:
        pass

    @abstractmethod
    async def delete(self, chat_id: int) -> bool:
        pass

    @abstractmethod
    async def add_member(self, chat_id: int, user_id: int) -> Optional[schemas.Chat]:
        pass

    @abstractmethod
    async def remove_member(self, chat_id: int, user_id: int) -> bool:
        pass

    @abstractmethod
    async def start_chat(self, current_user_id: int, other_user_id: int) -> Optional[schemas.Chat]:
        pass


class AbstractMessageRepository(ABC):
    @abstractmethod
    async def get_by_id(self, message_id: int, user_id: int) -> Optional[schemas.Message]:
        pass

    @abstractmethod
    async def get_all(self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100,
                      content: Optional[str] = None) -> List[schemas.Message]:
        pass

    @abstractmethod
    async def create(self, message: schemas.MessageCreate, user_id: int) -> schemas.Message:
        pass

    @abstractmethod
    async def update(self, message_id: int, message_update: schemas.MessageUpdate, user_id: int) -> Optional[
        schemas.Message]:
        pass

    @abstractmethod
    async def delete(self, message_id: int, user_id: int) -> bool:
        pass
