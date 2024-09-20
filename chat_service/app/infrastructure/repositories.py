# app/infrastructure/repositories.py

from typing import Optional, List

from app.domain import models, schemas
from app.domain.interfaces import (AbstractUserRepository, AbstractChatRepository,
                                   AbstractMessageRepository, AbstractTokenRepository)
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload


class SQLAlchemyUserRepository(AbstractUserRepository):
    def __init__(self, session: AsyncSession, security_service):
        self.session = session
        self.security_service = security_service

    async def get_by_id(self, user_id: int) -> Optional[models.User]:
        result = await self.session.execute(select(models.User).filter(models.User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[models.User]:
        result = await self.session.execute(select(models.User).filter(models.User.username == username))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100, username: str = None) -> List[models.User]:
        query = select(models.User)
        if username:
            query = query.filter(models.User.username.ilike(f"%{username}%"))
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, user: schemas.UserCreate) -> models.User:
        hashed_password = self.security_service.get_password_hash(user.password)
        db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
        self.session.add(db_user)
        await self.session.commit()
        return db_user

    async def update(self, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
        db_user = await self.get_by_id(user_id)
        if not db_user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = self.security_service.get_password_hash(update_data.pop("password"))

        for key, value in update_data.items():
            setattr(db_user, key, value)

        await self.session.commit()
        return db_user

    async def delete(self, user_id: int) -> bool:
        db_user = await self.get_by_id(user_id)
        if not db_user:
            return False
        await self.session.delete(db_user)
        await self.session.commit()
        return True

    async def search_users(self, query: str, current_user_id: int) -> List[models.User]:
        stmt = select(models.User).filter(
            models.User.id != current_user_id,
            or_(
                models.User.username.ilike(f"%{query}%"),
                models.User.email.ilike(f"%{query}%")
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class SQLAlchemyChatRepository(AbstractChatRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, chat_id: int, user_id: int) -> Optional[models.Chat]:
        stmt = select(models.Chat).options(selectinload(models.Chat.members)).filter(
            models.Chat.id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_all(self, user_id: int, skip: int = 0, limit: int = 100, name: str = None) -> List[models.Chat]:
        stmt = select(models.Chat).options(selectinload(models.Chat.members)).filter(
            models.Chat.members.any(id=user_id))
        if name:
            stmt = stmt.filter(models.Chat.name.ilike(f"%{name}%"))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, chat: schemas.ChatCreate, user_id: int) -> models.Chat:
        db_chat = models.Chat(name=chat.name)
        members = await self.session.execute(
            select(models.User).filter(models.User.id.in_([user_id] + chat.member_ids)))
        db_chat.members = members.scalars().all()
        self.session.add(db_chat)
        await self.session.commit()
        return db_chat

    async def update(self, chat_id: int, chat_update: schemas.ChatUpdate, user_id: int) -> Optional[models.Chat]:
        db_chat = await self.get_by_id(chat_id, user_id)
        if not db_chat:
            return None

        update_data = chat_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "member_ids":
                members = await self.session.execute(select(models.User).filter(models.User.id.in_(value)))
                db_chat.members = members.scalars().all()
            else:
                setattr(db_chat, key, value)

        await self.session.commit()
        return db_chat

    async def delete(self, chat_id: int, user_id: int) -> bool:
        db_chat = await self.get_by_id(chat_id, user_id)
        if not db_chat:
            return False
        await self.session.delete(db_chat)
        await self.session.commit()
        return True

    async def add_member(self, chat_id: int, user_id: int, current_user_id: int) -> Optional[models.Chat]:
        db_chat = await self.get_by_id(chat_id, current_user_id)
        if not db_chat:
            return None

        db_user = await self.session.execute(select(models.User).filter(models.User.id == user_id))
        db_user = db_user.scalar_one_or_none()
        if not db_user:
            return None

        db_chat.members.append(db_user)
        await self.session.commit()
        await self.session.refresh(db_chat, ['members'])

        return db_chat

    async def remove_member(self, chat_id: int, user_id: int, current_user_id: int) -> bool:
        db_chat = await self.get_by_id(chat_id, current_user_id)
        if not db_chat:
            return False

        db_user = await self.session.execute(select(models.User).filter(models.User.id == user_id))
        db_user = db_user.scalar_one_or_none()
        if not db_user:
            return False

        if db_user in db_chat.members:
            db_chat.members.remove(db_user)
            await self.session.commit()

        return True

    async def start_chat(self, current_user_id: int, other_user_id: int) -> Optional[models.Chat]:
        stmt = select(models.Chat).filter(
            models.Chat.members.any(id=current_user_id),
            models.Chat.members.any(id=other_user_id)
        ).join(models.Chat.members).group_by(models.Chat.id).having(func.count(models.User.id) == 2)
        result = await self.session.execute(stmt)
        existing_chat = result.scalar_one_or_none()

        if existing_chat:
            return existing_chat

        current_user = await self.session.execute(select(models.User).filter(models.User.id == current_user_id))
        other_user = await self.session.execute(select(models.User).filter(models.User.id == other_user_id))
        current_user = current_user.scalar_one_or_none()
        other_user = other_user.scalar_one_or_none()

        if not other_user:
            return None

        new_chat = models.Chat(name=f"Chat with {other_user.username}")
        new_chat.members = [current_user, other_user]
        self.session.add(new_chat)
        await self.session.commit()
        return new_chat

    async def get_unread_messages_count(self, chat_id: int, user_id: int) -> int:
        stmt = select(func.count()).select_from(models.Message).join(
            models.MessageStatus,
            (models.Message.id == models.MessageStatus.message_id) &
            (models.MessageStatus.user_id == user_id)
        ).filter(
            models.Message.chat_id == chat_id,
            models.MessageStatus.is_read == False
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_chat_members(self, chat_id: int) -> List[models.User]:
        stmt = select(models.User).join(models.chat_members).filter(models.chat_members.c.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class SQLAlchemyMessageRepository(AbstractMessageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, message_id: int, user_id: int) -> Optional[models.Message]:
        stmt = select(models.Message).options(joinedload(models.Message.user)).join(models.Chat).filter(
            models.Message.id == message_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_all(self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100, content: str = None) -> List[
        models.Message]:
        stmt = select(models.Message).options(joinedload(models.Message.user)).join(models.Chat).filter(
            models.Message.chat_id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        if content:
            stmt = stmt.filter(models.Message.content.ilike(f"%{content}%"))
        stmt = stmt.order_by(models.Message.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.unique().scalars().all()

    async def check_chat_exists_and_user_is_member(self, chat_id: int, user_id: int) -> bool:
        stmt = select(models.Chat).filter(
            models.Chat.id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, message: schemas.MessageCreate, user_id: int) -> models.Message:
        db_message = models.Message(content=message.content, chat_id=message.chat_id, user_id=user_id)
        self.session.add(db_message)
        await self.session.flush()

        # Fetch the chat with members eagerly loaded
        stmt = select(models.Chat).options(joinedload(models.Chat.members)).filter(models.Chat.id == message.chat_id)
        result = await self.session.execute(stmt)
        chat = result.unique().scalar_one()

        current_time = func.now()

        for member in chat.members:
            is_author = member.id == user_id
            status = models.MessageStatus(
                message_id=db_message.id,
                user_id=member.id,
                is_read=is_author,
                read_at=current_time if is_author else None
            )
            self.session.add(status)

        await self.session.commit()
        await self.session.refresh(db_message)
        return db_message

    async def update_message_status(self, message_id: int, user_id: int, status_update: schemas.MessageStatusUpdate) -> \
    Optional[models.Message]:
        # First, update the message status
        stmt = select(models.MessageStatus).filter(
            models.MessageStatus.message_id == message_id,
            models.MessageStatus.user_id == user_id
        )
        result = await self.session.execute(stmt)
        db_status = result.scalar_one_or_none()

        if not db_status:
            return None

        db_status.is_read = status_update.is_read
        if status_update.is_read:
            db_status.read_at = func.now()

        await self.session.commit()

        # Then, fetch the updated message separately
        stmt = select(models.Message).options(
            joinedload(models.Message.user),
            joinedload(models.Message.statuses)
        ).filter(models.Message.id == message_id)
        result = await self.session.execute(stmt)
        message = result.unique().scalar_one_or_none()

        return message

    async def update(self, message_id: int, message_update: schemas.MessageUpdate, user_id: int) -> Optional[
        models.Message]:
        db_message = await self.get_by_id(message_id, user_id)
        if not db_message or db_message.user_id != user_id:
            return None

        db_message.content = message_update.content
        db_message.updated_at = func.now()
        await self.session.commit()
        await self.session.refresh(db_message)
        return db_message

    async def delete(self, message_id: int, user_id: int) -> Optional[models.Message]:
        db_message = await self.get_by_id(message_id, user_id)
        if not db_message or db_message.user_id != user_id:
            return None

        db_message.is_deleted = True
        db_message.content = "<This message has been deleted>"
        await self.session.commit()
        await self.session.refresh(db_message)
        return db_message


class SQLAlchemyTokenRepository(AbstractTokenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, token: schemas.TokenCreate) -> models.Token:
        db_token = models.Token(**token.model_dump())
        self.session.add(db_token)
        await self.session.commit()
        return db_token

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

    async def update(self, token: models.Token) -> models.Token:
        self.session.add(token)
        await self.session.commit()
        return token

    async def delete(self, token_id: int) -> bool:
        stmt = select(models.Token).filter(models.Token.id == token_id)
        result = await self.session.execute(stmt)
        db_token = result.scalar_one_or_none()
        if not db_token:
            return False
        await self.session.delete(db_token)
        await self.session.commit()
        return True

    async def delete_by_access_token(self, access_token: str) -> bool:
        stmt = select(models.Token).filter(models.Token.access_token == access_token)
        result = await self.session.execute(stmt)
        db_token = result.scalar_one_or_none()
        if not db_token:
            return False
        await self.session.delete(db_token)
        await self.session.commit()
        return True
