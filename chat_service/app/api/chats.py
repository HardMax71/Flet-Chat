# app/api/chats.py

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.dependencies import (
    get_chat_interactor,
    get_current_active_user,
    get_user_interactor,
)
from app.infrastructure import schemas
from app.interactors.chat_interactor import ChatInteractor
from app.interactors.user_interactor import UserInteractor

router = APIRouter()


@router.post("/", response_model=schemas.Chat)
async def create_chat(
    chat: schemas.ChatCreate,
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    new_chat = await chat_interactor.create_chat(chat, current_user.id)
    if not new_chat:
        raise HTTPException(status_code=404, detail="One or more invalid member IDs")
    return new_chat


@router.get("/", response_model=list[schemas.Chat])
async def read_chats(
    skip: int = 0,
    limit: int = 100,
    name: str | None = Query(None, description="Filter chats by name"),
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    chats = await chat_interactor.get_chats(
        current_user.id, skip=skip, limit=limit, name=name
    )
    return chats


@router.post("/start", response_model=schemas.Chat)
async def start_chat(
    other_user_id: int = Body(
        ..., embed=True, description="ID of the user to start a chat with"
    ),
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    chat = await chat_interactor.start_chat(current_user.id, other_user_id)
    if not chat:
        raise HTTPException(status_code=404, detail="User not found")
    return chat


@router.get("/{chat_id}", response_model=schemas.Chat)
async def read_chat(
    chat_id: int,
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    chat = await chat_interactor.get_chat(chat_id, current_user.id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.put("/{chat_id}", response_model=schemas.Chat)
async def update_chat(
    chat_id: int,
    chat_update: schemas.ChatUpdate,
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    updated_chat = await chat_interactor.update_chat(
        chat_id, chat_update, current_user.id
    )
    if updated_chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return updated_chat


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: int,
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    deleted = await chat_interactor.delete_chat(chat_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.get("/{chat_id}/members", response_model=list[schemas.User])
async def get_chat_members(
    chat_id: int,
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    chat = await chat_interactor.get_chat(chat_id, current_user.id)
    if not chat:
        raise HTTPException(
            status_code=404, detail="Chat not found or you're not a member"
        )
    return chat.members


@router.post("/{chat_id}/members", response_model=schemas.Chat)
async def add_chat_member(
    chat_id: int,
    user_id: int = Body(..., embed=True),
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    user_interactor: UserInteractor = Depends(get_user_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    user = await user_interactor.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat = await chat_interactor.add_member(chat_id, user_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return chat


@router.delete("/{chat_id}/members/{user_id}", status_code=204)
async def remove_chat_member(
    chat_id: int,
    user_id: int,
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    user_interactor: UserInteractor = Depends(get_user_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    user = await user_interactor.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat = await chat_interactor.remove_member(chat_id, user_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.get("/{chat_id}/unread_count", response_model=int)
async def get_unread_messages_count(
    chat_id: int,
    chat_interactor: ChatInteractor = Depends(get_chat_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    unread_count = await chat_interactor.get_unread_messages_count(
        chat_id, current_user.id
    )
    if unread_count is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return unread_count
