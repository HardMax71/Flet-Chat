# app/infrastructure/message_gateway.py
from datetime import datetime, timezone
from typing import List, Optional

from app.gateways.interfaces import IMessageGateway
from app.infrastructure import models
from app.infrastructure import schemas
from app.infrastructure.data_mappers import MessageMapper
from app.infrastructure.uow import UnitOfWork, UoWModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class MessageGateway(IMessageGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        uow.mappers[models.Message] = MessageMapper(session)

    async def get_message(self, message_id: int, user_id: int) -> Optional[UoWModel]:
        stmt = select(models.Message).join(models.Chat).filter(
            models.Message.id == message_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()
        return UoWModel(message, self.uow) if message else None

    async def get_all(self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100,
                      content: Optional[str] = None) -> List[UoWModel]:
        stmt = select(models.Message).join(models.Chat).filter(
            models.Message.chat_id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        if content:
            stmt = stmt.filter(models.Message.content.ilike(f"%{content}%"))
        stmt = stmt.order_by(models.Message.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        messages = result.scalars().all()
        return [UoWModel(message, self.uow) for message in messages]

    async def create_message(self, message: schemas.MessageCreate, user_id: int) -> UoWModel:
        chat_stmt = select(models.Chat).filter(models.Chat.id == message.chat_id, models.Chat.members.any(id=user_id))
        chat_result = await self.session.execute(chat_stmt)
        chat = chat_result.scalar_one_or_none()

        if not chat:
            raise ValueError(f"Chat with id {message.chat_id} not found or user is not a member")

        db_message = models.Message(content=message.content, chat_id=message.chat_id, user_id=user_id)
        for member in chat.members:
            is_author = member.id == user_id
            message_status = models.MessageStatus(
                user_id=member.id,
                is_read=is_author,
                read_at=datetime.now(timezone.utc) if is_author else None
            )
            db_message.statuses.append(message_status)

        uow_message = self.uow.register_new(db_message)
        await self.uow.commit()
        return uow_message

    async def update_message(self, message_id: int, message_update: schemas.MessageUpdate, user_id: int) -> Optional[
        UoWModel]:
        stmt = select(models.Message).join(models.Chat).filter(
            models.Message.id == message_id,
            models.Message.user_id == user_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()
        if message:
            message.content = message_update.content
            message.updated_at = datetime.now(timezone.utc)
            uow_message = UoWModel(message, self.uow)
            self.uow.register_dirty(message)
            await self.uow.commit()
            return uow_message
        return None

    async def delete_message(self, message_id: int, user_id: int) -> Optional[UoWModel]:
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
            message.updated_at = datetime.now(timezone.utc)
            uow_message = UoWModel(message, self.uow)
            self.uow.register_dirty(message)
            await self.uow.commit()
            return uow_message
        return None

    async def update_message_status(self, message_id: int, user_id: int, status_update: schemas.MessageStatusUpdate) -> \
            Optional[UoWModel]:
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
            else:
                new_status = models.MessageStatus(
                    message_id=message_id,
                    user_id=user_id,
                    is_read=status_update.is_read,
                    read_at=datetime.utcnow() if status_update.is_read else None
                )
                message.statuses.append(new_status)
            uow_message = UoWModel(message, self.uow)
            self.uow.register_dirty(message)
            await self.uow.commit()
            return uow_message
        return None
