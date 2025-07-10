# app/main.py
import logging
import sys
from contextlib import asynccontextmanager

from app.api import users, chats, messages, auth
from app.config import AppConfig
from app.infrastructure.database import create_database
from app.infrastructure.event_dispatcher import EventDispatcher
from app.infrastructure.event_handlers import EventHandlers
from app.infrastructure.redis_client import RedisClient
from app.infrastructure.security import SecurityService
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine


class Application:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = self.setup_logger()
        engine = create_async_engine(config.DATABASE_URL, echo=False)
        self.database = create_database(engine)
        self.redis_client = RedisClient(
            config.REDIS_HOST, config.REDIS_PORT, self.logger
        )
        self.event_dispatcher = EventDispatcher()
        self.security_service = SecurityService(config)
        self.event_handlers = EventHandlers(self.redis_client)

        # Register event handlers
        self.event_dispatcher.register(
            "MessageCreated", self.event_handlers.publish_message_created
        )
        self.event_dispatcher.register(
            "MessageUpdated", self.event_handlers.publish_message_updated
        )
        self.event_dispatcher.register(
            "MessageDeleted", self.event_handlers.publish_message_deleted
        )
        self.event_dispatcher.register(
            "MessageStatusUpdated", self.event_handlers.publish_message_status_updated
        )
        self.event_dispatcher.register(
            "UnreadCountUpdated", self.event_handlers.publish_unread_count_updated
        )

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        await self.database.connect()
        await self.redis_client.connect()
        yield
        await self.database.disconnect()
        await self.redis_client.disconnect()

    def setup_logger(self):
        logger = logging.getLogger("ChatAPI")
        logger.setLevel(logging.INFO)

        c_handler = logging.StreamHandler(sys.stdout)
        # file logs turned off for now
        # f_handler = RotatingFileHandler('chat_api.log', maxBytes=10 * 1024 * 1024, backupCount=5)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        c_handler.setFormatter(formatter)
        # f_handler.setFormatter(formatter)

        logger.addHandler(c_handler)
        # logger.addHandler(f_handler)

        return logger

    def create_app(self) -> FastAPI:
        app = FastAPI(
            title=self.config.PROJECT_NAME,
            version=self.config.PROJECT_VERSION,
            description=self.config.PROJECT_DESCRIPTION,
            openapi_url=f"{self.config.API_V1_STR}/openapi.json",
            lifespan=self.lifespan,
        )

        app.state.config = self.config
        app.state.security_service = self.security_service
        app.state.event_dispatcher = self.event_dispatcher
        app.state.database = self.database
        app.state.logger = self.logger

        # Create routers
        app.include_router(
            auth.router, prefix=f"{self.config.API_V1_STR}/auth", tags=["auth"]
        )
        app.include_router(
            users.router, prefix=f"{self.config.API_V1_STR}/users", tags=["users"]
        )
        app.include_router(
            chats.router, prefix=f"{self.config.API_V1_STR}/chats", tags=["chats"]
        )
        app.include_router(
            messages.router,
            prefix=f"{self.config.API_V1_STR}/messages",
            tags=["messages"],
        )

        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            return JSONResponse(
                status_code=500,
                content={"message": f"An unexpected error occurred: {str(exc)}"},
            )

        return app


def create():
    config = AppConfig()
    application = Application(config)
    app = application.create_app()
    application.logger.info("Application created and configured")

    return app


app = create()


@app.get("/")
async def root():
    return {"message": "Welcome to the Chat API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
