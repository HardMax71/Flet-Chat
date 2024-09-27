# app/gateways/chat_gateway.py
from typing import List, Optional, Dict

from app.domain import models
from app.infrastructure import schemas
from app.infrastructure.data_mappers import ChatMapper
from app.infrastructure.uow import UnitOfWork, UoWModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class ChatGateway:
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        uow.mappers[models.Chat] = ChatMapper(session)

    async def get_chat(self, chat_id: int, user_id: int) -> Optional[UoWModel]:
        stmt = select(models.Chat).filter(models.Chat.id == chat_id, models.Chat.members.any(id=user_id))
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()
        return UoWModel(chat, self.uow) if chat else None

    async def get_all(self, user_id: int, skip: int = 0, limit: int = 100, name: Optional[str] = None) -> List[
        UoWModel]:
        stmt = select(models.Chat).filter(models.Chat.members.any(id=user_id))
        if name:
            stmt = stmt.filter(models.Chat.name.ilike(f"%{name}%"))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        chats = result.scalars().all()
        return [UoWModel(chat, self.uow) for chat in chats]

    async def create_chat(self, chat: schemas.ChatCreate, user_id: int) -> UoWModel:
        db_chat = models.Chat(name=chat.name)
        stmt = select(models.User).filter(models.User.id.in_(chat.member_ids + [user_id]))
        result = await self.session.execute(stmt)
        members = result.scalars().all()
        db_chat.members = members
        uow_chat = self.uow.register_new(db_chat)
        await self.uow.commit()
        return uow_chat

    async def add_member(self, chat_id: int, user_id: int, current_user_id: int) -> Optional[UoWModel]:
        chat = await self.get_chat(chat_id, current_user_id)
        if not chat:
            return None
        stmt = select(models.User).filter(models.User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            chat._model.members.append(user)
            self.uow.register_dirty(chat._model)
            await self.uow.commit()
        return chat

    async def delete_chat(self, chat_id: int, user_id: int) -> None:
        chat = await self.get_chat(chat_id, user_id)
        if chat:
            self.uow.register_deleted(chat._model)
            await self.uow.commit()

    async def remove_member(self, chat_id: int, user_id: int, current_user_id: int) -> bool:
        chat = await self.get_chat(chat_id, current_user_id)
        if not chat:
            return False
        chat._model.members = [m for m in chat._model.members if m.id != user_id]
        self.uow.register_dirty(chat._model)
        await self.uow.commit()
        return True

    async def start_chat(self, current_user_id: int, other_user_id: int) -> Optional[UoWModel]:
        stmt = select(models.User).filter(models.User.id.in_([current_user_id, other_user_id]))
        result = await self.session.execute(stmt)
        members = result.scalars().all()
        if len(members) != 2:
            return None
        db_chat = models.Chat(name=f"Chat between {members[0].username} and {members[1].username}")
        db_chat.members = members
        uow_chat = self.uow.register_new(db_chat)
        await self.uow.commit()
        return uow_chat

    async def get_user_ids_in_chat(self, chat_id: int) -> List[int]:
        stmt = select(models.Chat).options(selectinload(models.Chat.members)).filter(models.Chat.id == chat_id)
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()
        if not chat:
            return []
        return [user.id for user in chat.members]

    async def get_unread_messages_count(self, chat_id: int, user_id: int) -> int:
        stmt = select(func.count(models.MessageStatus.id)).join(models.Message).filter(
            models.Message.chat_id == chat_id, models.MessageStatus.user_id == user_id,
            models.MessageStatus.is_read == False)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_unread_counts_for_chat_members(self, chat_id: int, current_user_id: int) -> Dict[int, int]:
        stmt = select(models.MessageStatus.user_id, func.count(models.MessageStatus.id).label('unread_count')).join(
            models.Message).filter(models.Message.chat_id == chat_id, models.MessageStatus.is_read == False,
                                   models.MessageStatus.user_id != current_user_id).group_by(
            models.MessageStatus.user_id)
        result = await self.session.execute(stmt)
        return {row.user_id: row.unread_count for row in result}
