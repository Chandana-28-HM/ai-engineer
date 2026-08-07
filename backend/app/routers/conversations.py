from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Conversation, Message, Project
from app.schemas import ConversationCreate, ConversationRead, MessageRead

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
async def list_conversations(project_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Conversation).order_by(Conversation.updated_at.desc())
    if project_id is not None:
        query = query.where(Conversation.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars())


@router.post("", response_model=ConversationRead, status_code=201)
async def create_conversation(payload: ConversationCreate, db: AsyncSession = Depends(get_db)):
    if payload.project_id is not None:
        project = await db.get(Project, payload.project_id)
        if project is None:
            raise HTTPException(404, "Project not found")
    conversation = Conversation(project_id=payload.project_id, title=payload.title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def rename_conversation(conversation_id: int, payload: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    if payload.title:
        conversation.title = payload.title
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    await db.delete(conversation)
    await db.commit()


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(conversation_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    return list(result.scalars())
