# app/gateways/chat_gateway.py
from typing import List, Optional

from app.domain import models, schemas
from app.infrastructure.uow import UnitOfWork, UoWModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class ChatGateway:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_chat(self, chat_id: int, user_id: int) -> Optional[UoWModel]:
        chat = await self.uow.mappers[models.Chat].get_chat(chat_id, user_id)
        return UoWModel(chat, self.uow) if chat else None

    async def get_all(self, user_id: int, skip: int = 0, limit: int = 100, name: Optional[str] = None) -> List[
        UoWModel]:
        chats = await self.uow.mappers[models.Chat].get_all(user_id, skip, limit, name)
        return [UoWModel(chat, self.uow) for chat in chats]

    async def create_chat(self, chat: schemas.ChatCreate, user_id: int) -> UoWModel:
        db_chat = models.Chat(name=chat.name)
        members = await self.uow.mappers[models.Chat].get_users_by_ids(chat.member_ids + [user_id])
        db_chat.members = members
        return self.uow.register_new(db_chat)

    async def add_member(self, chat_id: int, user_id: int, current_user_id: int) -> Optional[UoWModel]:
        chat = await self.get_chat(chat_id, current_user_id)
        if not chat:
            return None
        user = await self.uow.mappers[models.User].get_by_id(user_id)
        if user:
            chat._model.members.append(user)
            self.uow.register_dirty(chat._model)
        return chat

    async def remove_member(self, chat_id: int, user_id: int, current_user_id: int) -> bool:
        chat = await self.get_chat(chat_id, current_user_id)
        if not chat:
            return False
        chat._model.members = [m for m in chat._model.members if m.id != user_id]
        self.uow.register_dirty(chat._model)
        return True

    async def start_chat(self, current_user_id: int, other_user_id: int) -> Optional[UoWModel]:
        members = await self.uow.mappers[models.Chat].get_users_by_ids([current_user_id, other_user_id])
        if len(members) != 2:
            return None
        db_chat = models.Chat(name=f"Chat between {members[0].username} and {members[1].username}")
        db_chat.members = members
        return self.uow.register_new(db_chat)

    async def get_user_ids_in_chat(self, chat_id: int) -> List[int]:
        stmt = select(models.Chat).options(selectinload(models.Chat.members)).filter(models.Chat.id == chat_id)
        result = await self.uow.session.execute(stmt)
        chat = result.scalar_one_or_none()
        if not chat:
            return []
        return [user.id for user in chat.members]

    async def get_unread_messages_count(self, chat_id: int, user_id: int) -> int:
        return await self.uow.mappers[models.Message].get_unread_messages_count(chat_id, user_id)