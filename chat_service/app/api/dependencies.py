# app/api/dependencies.py
from typing import AsyncGenerator
from app.config import AppConfig
from app.gateways.chat_gateway import ChatGateway
from app.gateways.message_gateway import MessageGateway
from app.gateways.token_gateway import TokenGateway
from app.gateways.user_gateway import UserGateway
from app.infrastructure import schemas
from app.infrastructure.event_dispatcher import EventDispatcher
from app.infrastructure.security import SecurityService
from app.infrastructure.uow import UnitOfWork
from app.interactors.chat_interactor import ChatInteractor
from app.interactors.message_interactor import MessageInteractor
from app.interactors.token_interactor import TokenInteractor
from app.interactors.user_interactor import UserInteractor
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_security_service(request: Request) -> SecurityService:
    return request.app.state.security_service


def get_event_dispatcher(request: Request) -> EventDispatcher:
    return request.app.state.event_dispatcher


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.database.session() as session:
        try:
            yield session
            await session.commit()  # Commit the transaction
        except Exception:
            await session.rollback()  # Rollback in case of error
            raise


async def get_uow() -> UnitOfWork:
    return UnitOfWork()


async def get_user_gateway(
    session: AsyncSession = Depends(get_session), uow: UnitOfWork = Depends(get_uow)
):
    return UserGateway(session, uow)


async def get_chat_gateway(
    session: AsyncSession = Depends(get_session), uow: UnitOfWork = Depends(get_uow)
):
    return ChatGateway(session, uow)


async def get_message_gateway(
    session: AsyncSession = Depends(get_session), uow: UnitOfWork = Depends(get_uow)
):
    return MessageGateway(session, uow)


async def get_token_gateway(
    session: AsyncSession = Depends(get_session), uow: UnitOfWork = Depends(get_uow)
):
    return TokenGateway(session, uow)


async def get_user_interactor(
    security_service: SecurityService = Depends(get_security_service),
    user_gateway: UserGateway = Depends(get_user_gateway),
):
    return UserInteractor(security_service, user_gateway)


async def get_chat_interactor(
    chat_gateway: ChatGateway = Depends(get_chat_gateway),
    user_gateway: UserGateway = Depends(get_user_gateway),
):
    return ChatInteractor(chat_gateway, user_gateway)


async def get_message_interactor(
    message_gateway: MessageGateway = Depends(get_message_gateway),
):
    return MessageInteractor(message_gateway)


async def get_token_interactor(
    token_gateway: TokenGateway = Depends(get_token_gateway),
):
    return TokenInteractor(token_gateway)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    security_service: SecurityService = Depends(get_security_service),
    user_gateway: UserGateway = Depends(get_user_gateway),
    token_gateway: TokenGateway = Depends(get_token_gateway),
) -> schemas.User:
    username = security_service.decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_model = await user_gateway.get_by_username(username)
    valid_token = await token_gateway.get_by_access_token(token)
    if user_model is None or valid_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user_model._model.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.User.model_validate(user_model._model)


async def get_current_active_user(
    current_user: schemas.User = Depends(get_current_user),
) -> schemas.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
