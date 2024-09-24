# app/infrastructure/data_mappers.py
from datetime import datetime
from typing import Protocol, TypeVar, List, Optional

from app.domain import models, schemas
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

ModelT = TypeVar('ModelT')


class DataMapper(Protocol[ModelT]):
    async def insert(self, model: ModelT):
        raise NotImplementedError

    async def delete(self, model: ModelT):
        raise NotImplementedError

    async def update(self, model: ModelT):
        raise NotImplementedError


class UserMapper(DataMapper[models.User]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, model: models.User):
        self.session.add(model)
        await self.session.flush()

    async def delete(self, model: models.User):
        await self.session.delete(model)

    async def update(self, model: models.User):
        await self.session.merge(model)

    async def get_by_id(self, user_id: int) -> Optional[models.User]:
        result = await self.session.execute(select(models.User).filter(models.User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[models.User]:
        result = await self.session.execute(select(models.User).filter(models.User.username == username))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100, username: Optional[str] = None) -> List[models.User]:
        stmt = select(models.User)
        if username:
            stmt = stmt.filter(models.User.username.ilike(f"%{username}%"))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_users(self, query: str, current_user_id: int) -> List[models.User]:
        stmt = select(models.User).filter(models.User.id != current_user_id, models.User.username.ilike(f'%{query}%'))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ChatMapper(DataMapper[models.Chat]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, model: models.Chat):
        self.session.add(model)
        await self.session.flush()

    async def delete(self, model: models.Chat):
        await self.session.delete(model)

    async def update(self, model: models.Chat):
        await self.session.merge(model)

    async def get_chat(self, chat_id: int, user_id: int) -> Optional[models.Chat]:
        stmt = select(models.Chat).filter(models.Chat.id == chat_id, models.Chat.members.any(id=user_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, user_id: int, skip: int = 0, limit: int = 100, name: Optional[str] = None) -> List[
        models.Chat]:
        stmt = select(models.Chat).filter(models.Chat.members.any(id=user_id))
        if name:
            stmt = stmt.filter(models.Chat.name.ilike(f"%{name}%"))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_users_by_ids(self, user_ids: List[int]) -> List[models.User]:
        stmt = select(models.User).filter(models.User.id.in_(user_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_unread_messages_count(self, chat_id: int, user_id: int) -> int:
        stmt = select(func.count(models.MessageStatus.id)).join(models.Message).filter(
            models.Message.chat_id == chat_id,
            models.MessageStatus.user_id == user_id,
            models.MessageStatus.is_read == False
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_unread_counts_for_chat_members(self, chat_id: int, current_user_id: int) -> dict:
        stmt = select(
            models.MessageStatus.user_id,
            func.count(models.MessageStatus.id).label('unread_count')
        ).join(models.Message).filter(
            models.Message.chat_id == chat_id,
            models.MessageStatus.is_read == False,
            models.MessageStatus.user_id != current_user_id
        ).group_by(models.MessageStatus.user_id)
        result = await self.session.execute(stmt)
        return {row.user_id: row.unread_count for row in result}


class MessageMapper(DataMapper[models.Message]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, model: models.Message):
        self.session.add(model)
        await self.session.flush()

    async def delete(self, model: models.Message):
        await self.session.delete(model)

    async def update(self, model: models.Message):
        await self.session.merge(model)

    async def delete_message(self, message_id: int, user_id: int) -> Optional[models.Message]:
        stmt = select(models.Message).join(models.Chat).filter(
            models.Message.id == message_id,
            models.Message.user_id == user_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()
        if message:
            message.is_deleted = True
            message.content = "<This message has been deleted>"
            message.updated_at = datetime.utcnow()
            await self.session.flush()
        return message

    async def update_message(self, message_id: int, message_update: schemas.MessageUpdate, user_id: int) -> Optional[models.Message]:
        stmt = select(models.Message).join(models.Chat).filter(
            models.Message.id == message_id,
            models.Message.user_id == user_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()
        if message:
            message.content = message_update.content
            message.updated_at = datetime.utcnow()
            await self.session.flush()
        return message

    async def update_message_status(self, message_id: int, user_id: int, status_update: schemas.MessageStatusUpdate) -> \
    Optional[models.Message]:
        stmt = select(models.Message).options(
            selectinload(models.Message.statuses)
        ).filter(models.Message.id == message_id)
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if message:
            status = next((s for s in message.statuses if s.user_id == user_id), None)
            if status:
                status.is_read = status_update.is_read
                if status.is_read and not status.read_at:
                    status.read_at = datetime.utcnow()
                await self.session.flush()
            else:
                new_status = models.MessageStatus(
                    message_id=message_id,
                    user_id=user_id,
                    is_read=status_update.is_read,
                    read_at=datetime.utcnow() if status_update.is_read else None
                )
                message.statuses.append(new_status)
                await self.session.flush()
        return message

    async def create_message_with_statuses(self, message: models.Message,
                                           chat_members: List[models.User]) -> models.Message:
        self.session.add(message)
        for member in chat_members:
            is_author = member.id == message.user_id
            message_status = models.MessageStatus(
                user_id=member.id,
                is_read=is_author,
                read_at=datetime.utcnow() if is_author else None
            )
            message.statuses.append(message_status)
        await self.session.flush()
        return message

    async def get_message(self, message_id: int, user_id: int) -> Optional[models.Message]:
        stmt = select(models.Message).join(models.Chat).filter(
            models.Message.id == message_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100,
                      content: Optional[str] = None) -> List[models.Message]:
        stmt = select(models.Message).join(models.Chat).filter(
            models.Message.chat_id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        if content:
            stmt = stmt.filter(models.Message.content.ilike(f"%{content}%"))
        stmt = stmt.order_by(models.Message.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TokenMapper(DataMapper[models.Token]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, model: models.Token):
        self.session.add(model)
        await self.session.flush()

    async def delete(self, model: models.Token):
        await self.session.delete(model)

    async def update(self, model: models.Token):
        await self.session.merge(model)

    async def get_by_user_id(self, user_id: int) -> Optional[models.Token]:
        stmt = select(models.Token).filter(models.Token.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_access_token(self, access_token: str) -> Optional[models.Token]:
        stmt = select(models.Token).filter(models.Token.access_token == access_token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_refresh_token(self, refresh_token: str) -> Optional[models.Token]:
        stmt = select(models.Token).filter(models.Token.refresh_token == refresh_token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
