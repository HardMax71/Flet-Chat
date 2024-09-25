# app/api/dependencies.py
from app.config import AppConfig
from app.domain import schemas
from app.gateways.chat_gateway import ChatGateway
from app.gateways.message_gateway import MessageGateway
from app.gateways.token_gateway import TokenGateway
from app.gateways.user_gateway import UserGateway
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


async def get_session(request: Request) -> AsyncSession:
    async for session in request.app.state.database.get_session():
        try:
            yield session
            await session.commit()  # Commit the transaction
        except Exception:
            await session.rollback()  # Rollback in case of error
            raise


async def get_uow() -> UnitOfWork:
    return UnitOfWork()


async def get_user_gateway(session: AsyncSession = Depends(get_session), uow: UnitOfWork = Depends(get_uow)):
    return UserGateway(session, uow)


async def get_chat_gateway(session: AsyncSession = Depends(get_session), uow: UnitOfWork = Depends(get_uow)):
    return ChatGateway(session, uow)


async def get_message_gateway(session: AsyncSession = Depends(get_session), uow: UnitOfWork = Depends(get_uow)):
    return MessageGateway(session, uow)


async def get_token_gateway(session: AsyncSession = Depends(get_session), uow: UnitOfWork = Depends(get_uow)):
    return TokenGateway(session, uow)


async def get_user_interactor(
        uow: UnitOfWork = Depends(get_uow),
        security_service: SecurityService = Depends(get_security_service),
        user_gateway: UserGateway = Depends(get_user_gateway)
):
    return UserInteractor(uow, security_service, user_gateway)


async def get_chat_interactor(
        uow: UnitOfWork = Depends(get_uow),
        chat_gateway: ChatGateway = Depends(get_chat_gateway)
):
    return ChatInteractor(uow, chat_gateway)


async def get_message_interactor(
        uow: UnitOfWork = Depends(get_uow),
        message_gateway: MessageGateway = Depends(get_message_gateway)
):
    return MessageInteractor(uow, message_gateway)


async def get_token_interactor(
        uow: UnitOfWork = Depends(get_uow),
        token_gateway: TokenGateway = Depends(get_token_gateway)
):
    return TokenInteractor(uow, token_gateway)


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        security_service: SecurityService = Depends(get_security_service),
        user_gateway: UserGateway = Depends(get_user_gateway),
        token_gateway: TokenGateway = Depends(get_token_gateway),
        uow: UnitOfWork = Depends(get_uow)
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
    await uow.commit()  # Commit the transaction to ensure the user is properly loaded
    return schemas.User.model_validate(user_model)


async def get_current_active_user(
        current_user: schemas.User = Depends(get_current_user)
) -> schemas.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
