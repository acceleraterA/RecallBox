from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent.graph import run_agent_graph
from app.agent.schemas import AgentChatInput, AgentChatOut, AgentContentMemory


def _content_memory_from_payload(payload: AgentChatInput) -> AgentContentMemory:
    if payload.memory.content.messages:
        return payload.memory.content
    return AgentContentMemory(messages=payload.history)


def run_agent_chat(db: Session, user_id: int, payload: AgentChatInput) -> AgentChatOut:
    return run_agent_graph(
        db=db,
        user_id=user_id,
        message=payload.message.strip(),
        content_memory=_content_memory_from_payload(payload),
        structured_memory=payload.memory.structured,
        confirm_action=payload.confirm_action,
    )
