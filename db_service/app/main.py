# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api import users, chats, messages, auth
from app.infrastructure.database import engine
from app.domain import models
from app.config import settings

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
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