# app/infrastructure/repositories.py
from typing import Optional, List
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from app.domain import models, schemas
from app.domain.interfaces import AbstractUserRepository, AbstractChatRepository, AbstractMessageRepository, AbstractTokenRepository
from app.infrastructure.data_mappers import UserMapper, ChatMapper, MessageMapper, TokenMapper
from app.infrastructure.security import SecurityService

class SQLAlchemyUserRepository(AbstractUserRepository):
    def __init__(self, session: AsyncSession, security_service: SecurityService):
        self.session = session
        self.security_service = security_service

    async def get_by_id(self, user_id: int) -> Optional[schemas.User]:
        result = await self.session.execute(select(models.User).filter(models.User.id == user_id))
        user = result.scalar_one_or_none()
        return UserMapper.to_domain(user) if user else None

    async def get_by_username(self, username: str) -> Optional[schemas.User]:
        result = await self.session.execute(select(models.User).filter(models.User.username == username))
        user = result.scalar_one_or_none()
        return UserMapper.to_domain(user) if user else None

    async def get_all(self, skip: int = 0, limit: int = 100, username: str = None) -> List[schemas.User]:
        query = select(models.User)
        if username:
            query = query.filter(models.User.username.ilike(f"%{username}%"))
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [UserMapper.to_domain(user) for user in result.scalars().all()]

    async def create(self, user: schemas.UserCreate) -> schemas.User:
        hashed_password = self.security_service.get_password_hash(user.password)
        db_user = UserMapper.to_orm(user)
        db_user.hashed_password = hashed_password
        self.session.add(db_user)
        await self.session.flush()
        return UserMapper.to_domain(db_user)

    async def update(self, user_id: int, user_update: schemas.UserUpdate) -> Optional[schemas.User]:
        result = await self.session.execute(select(models.User).filter(models.User.id == user_id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = self.security_service.get_password_hash(update_data.pop("password"))

        for key, value in update_data.items():
            setattr(db_user, key, value)

        await self.session.flush()
        return UserMapper.to_domain(db_user)

    async def delete(self, user_id: int) -> bool:
        result = await self.session.execute(select(models.User).filter(models.User.id == user_id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            return False
        await self.session.delete(db_user)
        return True

    async def search_users(self, query: str, current_user_id: int) -> List[schemas.User]:
        stmt = select(models.User).filter(
            models.User.id != current_user_id,
            or_(
                models.User.username.ilike(f"%{query}%"),
                models.User.email.ilike(f"%{query}%")
            )
        )
        result = await self.session.execute(stmt)
        return [UserMapper.to_domain(user) for user in result.scalars().all()]

class SQLAlchemyChatRepository(AbstractChatRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, chat_id: int, user_id: int) -> Optional[schemas.Chat]:
        stmt = select(models.Chat).options(selectinload(models.Chat.members)).filter(
            models.Chat.id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        chat = result.unique().scalar_one_or_none()
        return ChatMapper.to_domain(chat) if chat else None

    async def get_all(self, user_id: int, skip: int = 0, limit: int = 100, name: str = None) -> List[schemas.Chat]:
        stmt = select(models.Chat).options(selectinload(models.Chat.members)).filter(
            models.Chat.members.any(id=user_id))
        if name:
            stmt = stmt.filter(models.Chat.name.ilike(f"%{name}%"))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return [ChatMapper.to_domain(chat) for chat in result.scalars().all()]

    async def create(self, chat: schemas.ChatCreate, user_id: int) -> schemas.Chat:
        db_chat = ChatMapper.to_orm(chat)
        members = await self.session.execute(
            select(models.User).filter(models.User.id.in_([user_id] + chat.member_ids)))
        db_chat.members = members.scalars().all()
        self.session.add(db_chat)
        await self.session.flush()
        return ChatMapper.to_domain(db_chat)

    async def update(self, chat_id: int, chat_update: schemas.ChatUpdate, user_id: int) -> Optional[schemas.Chat]:
        result = await self.session.execute(select(models.Chat).filter(models.Chat.id == chat_id))
        db_chat = result.scalar_one_or_none()
        if not db_chat:
            return None

        update_data = chat_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "member_ids":
                members = await self.session.execute(select(models.User).filter(models.User.id.in_(value)))
                db_chat.members = members.scalars().all()
            else:
                setattr(db_chat, key, value)

        await self.session.flush()
        return ChatMapper.to_domain(db_chat)

    async def delete(self, chat_id: int, user_id: int) -> bool:
        result = await self.session.execute(select(models.Chat).filter(models.Chat.id == chat_id))
        db_chat = result.scalar_one_or_none()
        if not db_chat:
            return False
        await self.session.delete(db_chat)
        return True

    async def add_member(self, chat_id: int, user_id: int, current_user_id: int) -> Optional[schemas.Chat]:
        result = await self.session.execute(
            select(models.Chat).options(selectinload(models.Chat.members)).filter(models.Chat.id == chat_id)
        )
        db_chat = result.unique().scalar_one_or_none()
        if not db_chat:
            return None

        user_result = await self.session.execute(select(models.User).filter(models.User.id == user_id))
        db_user = user_result.scalar_one_or_none()
        if not db_user:
            return None

        db_chat.members.append(db_user)
        await self.session.flush()
        return ChatMapper.to_domain(db_chat)

    async def remove_member(self, chat_id: int, user_id: int, current_user_id: int) -> bool:
        result = await self.session.execute(
            select(models.Chat).options(selectinload(models.Chat.members)).filter(models.Chat.id == chat_id)
        )
        db_chat = result.unique().scalar_one_or_none()
        if not db_chat:
            return False

        db_chat.members = [member for member in db_chat.members if member.id != user_id]
        await self.session.flush()
        return True

    async def start_chat(self, current_user_id: int, other_user_id: int) -> Optional[schemas.Chat]:
        stmt = select(models.Chat).filter(
            models.Chat.members.any(id=current_user_id),
            models.Chat.members.any(id=other_user_id)
        ).join(models.Chat.members).group_by(models.Chat.id).having(func.count(models.User.id) == 2)
        result = await self.session.execute(stmt)
        existing_chat = result.scalar_one_or_none()

        if existing_chat:
            return ChatMapper.to_domain(existing_chat)

        current_user = await self.session.execute(select(models.User).filter(models.User.id == current_user_id))
        other_user = await self.session.execute(select(models.User).filter(models.User.id == other_user_id))
        current_user = current_user.scalar_one_or_none()
        other_user = other_user.scalar_one_or_none()

        if not other_user:
            return None

        new_chat = models.Chat(name=f"Chat with {other_user.username}")
        new_chat.members = [current_user, other_user]
        self.session.add(new_chat)
        await self.session.flush()
        return ChatMapper.to_domain(new_chat)

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

    async def get_chat_members(self, chat_id: int) -> List[schemas.User]:
        stmt = select(models.User).join(models.chat_members).filter(models.chat_members.c.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return [UserMapper.to_domain(user) for user in result.scalars().all()]

class SQLAlchemyMessageRepository(AbstractMessageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, message_id: int, user_id: int) -> Optional[schemas.Message]:
        stmt = select(models.Message).options(joinedload(models.Message.user)).join(models.Chat).filter(
            models.Message.id == message_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        message = result.unique().scalar_one_or_none()
        return MessageMapper.to_domain(message) if message else None

    async def get_all(self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100, content: str = None) -> List[schemas.Message]:
        stmt = select(models.Message).options(joinedload(models.Message.user)).join(models.Chat).filter(
            models.Message.chat_id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        if content:
            stmt = stmt.filter(models.Message.content.ilike(f"%{content}%"))
        stmt = stmt.order_by(models.Message.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return [MessageMapper.to_domain(message) for message in result.unique().scalars().all()]

    async def check_chat_exists_and_user_is_member(self, chat_id: int, user_id: int) -> bool:
        stmt = select(models.Chat).filter(
            models.Chat.id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, message: schemas.MessageCreate, user_id: int) -> schemas.Message:
        db_message = MessageMapper.to_orm(message, user_id)
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

        await self.session.flush()
        await self.session.refresh(db_message)
        return MessageMapper.to_domain(db_message)

    async def update(self, message_id: int, message_update: schemas.MessageUpdate, user_id: int) -> Optional[schemas.Message]:
        result = await self.session.execute(
            select(models.Message).filter(models.Message.id == message_id, models.Message.user_id == user_id)
        )
        db_message = result.scalar_one_or_none()
        if not db_message:
            return None

        db_message.content = message_update.content
        db_message.updated_at = func.now()
        await self.session.flush()
        await self.session.refresh(db_message)
        return MessageMapper.to_domain(db_message)

    async def delete(self, message_id: int, user_id: int) -> Optional[schemas.Message]:
        result = await self.session.execute(
            select(models.Message).filter(models.Message.id == message_id, models.Message.user_id == user_id)
        )
        db_message = result.scalar_one_or_none()
        if not db_message:
            return None

        db_message.is_deleted = True
        db_message.content = "<This message has been deleted>"
        await self.session.flush()
        await self.session.refresh(db_message)
        return MessageMapper.to_domain(db_message)

    async def update_message_status(self, message_id: int, user_id: int, status_update: schemas.MessageStatusUpdate) -> Optional[schemas.Message]:
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

        await self.session.flush()

        # Fetch the updated message
        stmt = select(models.Message).options(
            joinedload(models.Message.user),
            joinedload(models.Message.statuses)
        ).filter(models.Message.id == message_id)
        result = await self.session.execute(stmt)
        message = result.unique().scalar_one_or_none()

        return MessageMapper.to_domain(message) if message else None


class SQLAlchemyTokenRepository(AbstractTokenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, token: schemas.TokenCreate) -> schemas.Token:
        db_token = TokenMapper.to_orm(token)
        self.session.add(db_token)
        await self.session.flush()
        return TokenMapper.to_domain(db_token)

    async def get_by_user_id(self, user_id: int) -> Optional[schemas.Token]:
        stmt = select(models.Token).filter(models.Token.user_id == user_id)
        result = await self.session.execute(stmt)
        token = result.scalar_one_or_none()
        return TokenMapper.to_domain(token) if token else None

    async def get_by_access_token(self, access_token: str) -> Optional[schemas.Token]:
        stmt = select(models.Token).filter(models.Token.access_token == access_token)
        result = await self.session.execute(stmt)
        token = result.scalar_one_or_none()
        return TokenMapper.to_domain(token) if token else None

    async def get_by_refresh_token(self, refresh_token: str) -> Optional[schemas.Token]:
        stmt = select(models.Token).filter(models.Token.refresh_token == refresh_token)
        result = await self.session.execute(stmt)
        token = result.scalar_one_or_none()
        return TokenMapper.to_domain(token) if token else None

    async def update(self, token: schemas.Token) -> schemas.Token:
        stmt = select(models.Token).filter(models.Token.id == token.id)
        result = await self.session.execute(stmt)
        db_token = result.scalar_one_or_none()
        if db_token:
            for key, value in token.model_dump().items():
                setattr(db_token, key, value)
            await self.session.flush()
            return TokenMapper.to_domain(db_token)
        return None

    async def delete(self, token_id: int) -> bool:
        stmt = select(models.Token).filter(models.Token.id == token_id)
        result = await self.session.execute(stmt)
        db_token = result.scalar_one_or_none()
        if not db_token:
            return False
        await self.session.delete(db_token)
        return True

    async def delete_by_access_token(self, access_token: str) -> bool:
        stmt = select(models.Token).filter(models.Token.access_token == access_token)
        result = await self.session.execute(stmt)
        db_token = result.scalar_one_or_none()
        if not db_token:
            return False
        await self.session.delete(db_token)
        return True