# app/infrastructure/message_gateway.py
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.gateways.interfaces import IMessageGateway
from app.infrastructure import models, schemas
from app.infrastructure.data_mappers import MessageMapper
from app.infrastructure.uow import UnitOfWork, UoWModel


class MessageGateway(IMessageGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        uow.mappers[models.Message] = MessageMapper(session)

    async def get_message(self, message_id: int, user_id: int) -> UoWModel | None:
        stmt = (
            select(models.Message)
            .options(selectinload(models.Message.statuses))
            .join(models.Chat)
            .filter(
                models.Message.id == message_id, models.Chat.members.any(id=user_id)
            )
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()
        return UoWModel(message, self.uow) if message else None

    async def get_all(
        self,
        chat_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        content: str | None = None,
    ) -> list[UoWModel]:
        stmt = (
            select(models.Message)
            .options(selectinload(models.Message.statuses))
            .join(models.Chat)
            .filter(
                models.Message.chat_id == chat_id, models.Chat.members.any(id=user_id)
            )
        )
        if content:
            stmt = stmt.filter(models.Message.content.ilike(f"%{content}%"))
        stmt = stmt.order_by(models.Message.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        messages = result.scalars().all()
        return [UoWModel(message, self.uow) for message in messages]

    async def create_message(
        self, message: schemas.MessageCreate, user_id: int
    ) -> UoWModel:
        chat_stmt = (
            select(models.Chat)
            .options(selectinload(models.Chat.members))
            .filter(
                models.Chat.id == message.chat_id, models.Chat.members.any(id=user_id)
            )
        )
        chat_result = await self.session.execute(chat_stmt)
        chat = chat_result.scalar_one_or_none()

        if not chat:
            raise ValueError(
                f"Chat with id {message.chat_id} not found or user is not a member"
            )

        db_message = models.Message(
            content=message.content,
            chat_id=message.chat_id,
            user_id=user_id,
            is_deleted=False,
        )
        for member in chat.members:
            is_author = member.id == user_id
            message_status = models.MessageStatus(
                message_id=0,  # Will be set after commit
                user_id=member.id,
                is_read=is_author,
                read_at=datetime.now(UTC) if is_author else None,
            )
            db_message.statuses.append(message_status)

        self.uow.register_new(db_message)
        await self.uow.commit()

        # Reload with proper eager loading for return
        stmt = (
            select(models.Message)
            .options(selectinload(models.Message.statuses))
            .filter(models.Message.id == db_message.id)
        )
        result = await self.session.execute(stmt)
        reloaded_message = result.scalar_one()
        return UoWModel(reloaded_message, self.uow)

    async def update_message(
        self, message_id: int, message_update: schemas.MessageUpdate, user_id: int
    ) -> UoWModel | None:
        stmt = (
            select(models.Message)
            .options(selectinload(models.Message.statuses))
            .join(models.Chat)
            .filter(
                models.Message.id == message_id,
                models.Message.user_id == user_id,
                models.Chat.members.any(id=user_id),
            )
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()
        if message:
            message.content = message_update.content
            message.updated_at = datetime.now(UTC)
            uow_message = UoWModel(message, self.uow)
            self.uow.register_dirty(message)
            await self.uow.commit()
            return uow_message
        return None

    async def delete_message(self, message_id: int, user_id: int) -> UoWModel | None:
        stmt = (
            select(models.Message)
            .options(selectinload(models.Message.statuses))
            .join(models.Chat)
            .filter(
                models.Message.id == message_id,
                models.Message.user_id == user_id,
                models.Chat.members.any(id=user_id),
            )
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()
        if message:
            message.is_deleted = True
            message.content = "<This message has been deleted>"
            message.updated_at = datetime.now(UTC)
            uow_message = UoWModel(message, self.uow)
            self.uow.register_dirty(message)
            await self.uow.commit()
            return uow_message
        return None

    async def update_message_status(
        self, message_id: int, user_id: int, status_update: schemas.MessageStatusUpdate
    ) -> UoWModel | None:
        stmt = (
            select(models.Message)
            .options(selectinload(models.Message.statuses))
            .filter(models.Message.id == message_id)
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if message:
            status = next((s for s in message.statuses if s.user_id == user_id), None)
            if status:
                status.is_read = status_update.is_read
                if status.is_read and not status.read_at:
                    status.read_at = datetime.now(UTC)
            else:
                new_status = models.MessageStatus(
                    message_id=message_id,
                    user_id=user_id,
                    is_read=status_update.is_read,
                    read_at=datetime.now(UTC) if status_update.is_read else None,
                )
                message.statuses.append(new_status)
            uow_message = UoWModel(message, self.uow)
            self.uow.register_dirty(message)
            await self.uow.commit()
            return uow_message
        return None
