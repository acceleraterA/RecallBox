from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.schemas import AgentChatInput, AgentChatOut
from app.agent.service import run_agent_chat
from app.auth import get_current_user
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatOut)
def chat_with_agent(
    payload: AgentChatInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentChatOut:
    return run_agent_chat(db=db, user_id=user.id, payload=payload)
