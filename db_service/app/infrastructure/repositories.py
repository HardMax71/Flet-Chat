# app/infrastructure/repositories.py
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.domain import models, schemas
from app.domain.interfaces import AbstractUserRepository, AbstractChatRepository, AbstractMessageRepository
from app.infrastructure.security import get_password_hash

class SQLAlchemyUserRepository(AbstractUserRepository):
    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, user_id: int):
        return self.session.query(models.User).filter(models.User.id == user_id).first()

    async def get_by_username(self, username: str):
        return self.session.query(models.User).filter(models.User.username == username).first()

    async def get_all(self, skip: int = 0, limit: int = 100, username: str = None):
        query = self.session.query(models.User)
        if username:
            query = query.filter(models.User.username.ilike(f"%{username}%"))
        return query.offset(skip).limit(limit).all()

    async def create(self, user: schemas.UserCreate):
        hashed_password = get_password_hash(user.password)
        db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
        self.session.add(db_user)
        self.session.flush()
        return db_user

    async def update(self, user_id: int, user_update: schemas.UserUpdate):
        db_user = await self.get_by_id(user_id)
        if not db_user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for key, value in update_data.items():
            setattr(db_user, key, value)

        self.session.flush()
        return db_user

    async def delete(self, user_id: int):
        db_user = await self.get_by_id(user_id)
        if not db_user:
            return False
        self.session.delete(db_user)
        self.session.flush()
        return True

    async def search_users(self, query: str, current_user_id: int):
        return self.session.query(models.User).filter(
            models.User.id != current_user_id,
            or_(
                models.User.username.ilike(f"%{query}%"),
                models.User.email.ilike(f"%{query}%")
            )
        ).all()

class SQLAlchemyChatRepository(AbstractChatRepository):
    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, chat_id: int, user_id: int):
        return self.session.query(models.Chat).filter(
            models.Chat.id == chat_id,
            models.Chat.members.any(id=user_id)
        ).first()

    async def get_all(self, user_id: int, skip: int = 0, limit: int = 100, name: str = None):
        query = self.session.query(models.Chat).filter(models.Chat.members.any(id=user_id))
        if name:
            query = query.filter(models.Chat.name.ilike(f"%{name}%"))
        return query.offset(skip).limit(limit).all()

    async def create(self, chat: schemas.ChatCreate, user_id: int):
        db_chat = models.Chat(name=chat.name)
        db_chat.members = self.session.query(models.User).filter(models.User.id.in_([user_id] + chat.member_ids)).all()
        self.session.add(db_chat)
        self.session.flush()
        return db_chat

    async def update(self, chat_id: int, chat_update: schemas.ChatUpdate):
        db_chat = self.session.query(models.Chat).filter(models.Chat.id == chat_id).first()
        if not db_chat:
            return None

        update_data = chat_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "member_ids":
                db_chat.members = self.session.query(models.User).filter(models.User.id.in_(value)).all()
            else:
                setattr(db_chat, key, value)

        self.session.flush()
        return db_chat

    async def delete(self, chat_id: int):
        db_chat = self.session.query(models.Chat).filter(models.Chat.id == chat_id).first()
        if not db_chat:
            return False
        self.session.delete(db_chat)
        self.session.flush()
        return True

    async def add_member(self, chat_id: int, user_id: int):
        db_chat = self.session.query(models.Chat).filter(models.Chat.id == chat_id).first()
        if not db_chat:
            return None

        db_user = self.session.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            return None

        if db_user not in db_chat.members:
            db_chat.members.append(db_user)
            self.session.flush()

        return db_chat

    async def remove_member(self, chat_id: int, user_id: int):
        db_chat = self.session.query(models.Chat).filter(models.Chat.id == chat_id).first()
        if not db_chat:
            return False

        db_user = self.session.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            return False

        if db_user in db_chat.members:
            db_chat.members.remove(db_user)
            self.session.flush()

        return True

    async def start_chat(self, current_user_id: int, other_user_id: int):
        existing_chat = self.session.query(models.Chat).filter(
            models.Chat.members.any(id=current_user_id),
            models.Chat.members.any(id=other_user_id)
        ).join(models.Chat.members).group_by(models.Chat.id).having(func.count(models.User.id) == 2).first()

        if existing_chat:
            return existing_chat

        current_user = self.session.query(models.User).filter(models.User.id == current_user_id).first()
        other_user = self.session.query(models.User).filter(models.User.id == other_user_id).first()

        if not other_user:
            return None

        new_chat = models.Chat(name=f"Chat with {other_user.username}")
        new_chat.members = [current_user, other_user]
        self.session.add(new_chat)
        self.session.flush()
        return new_chat

class SQLAlchemyMessageRepository(AbstractMessageRepository):
    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, message_id: int, user_id: int):
        return self.session.query(models.Message).join(models.Chat).filter(
            models.Message.id == message_id,
            models.Chat.members.any(id=user_id)
        ).first()

    async def get_all(self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100, content: str = None):
        query = self.session.query(models.Message).join(models.Chat).filter(
            models.Message.chat_id == chat_id,
            models.Chat.members.any(id=user_id)
        )
        if content:
            query = query.filter(models.Message.content.ilike(f"%{content}%"))
        return query.order_by(models.Message.created_at.desc()).offset(skip).limit(limit).all()

    async def create(self, message: schemas.MessageCreate, user_id: int):
        db_message = models.Message(content=message.content, chat_id=message.chat_id, user_id=user_id)
        self.session.add(db_message)
        self.session.flush()
        return db_message

    async def update(self, message_id: int, message_update: schemas.MessageUpdate, user_id: int):
        db_message = await self.get_by_id(message_id, user_id)
        if not db_message:
            return None

        if db_message.user_id != user_id:
            return None

        db_message.content = message_update.content
        db_message.updated_at = func.now()
        self.session.flush()
        return db_message

    async def delete(self, message_id: int, user_id: int):
        db_message = await self.get_by_id(message_id, user_id)
        if not db_message:
            return False

        if db_message.user_id != user_id:
            return False

        db_message.is_deleted = True
        db_message.content = "<This message has been deleted>"
        self.session.flush()
        return True