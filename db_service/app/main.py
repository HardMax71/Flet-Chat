# app/main.py
from contextlib import asynccontextmanager

from app.api import users, chats, messages, auth
from app.config import settings
from app.infrastructure.database import engine, Base
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.infrastructure.redis_config import get_redis_client

from app.infrastructure.redis_config import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await get_redis_client()
    yield
    # Shutdown
    await engine.dispose()
    await redis_client.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(users.router, prefix=settings.API_V1_STR, tags=["users"])
app.include_router(chats.router, prefix=settings.API_V1_STR, tags=["chats"])
app.include_router(messages.router, prefix=settings.API_V1_STR, tags=["messages"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"An unexpected error occurred: {str(exc)}"}
    )


@app.get("/")
async def root():
    return {"message": "Welcome to the Chat API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
