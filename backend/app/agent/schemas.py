from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class AgentHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class AgentContentMemory(BaseModel):
    messages: list[AgentHistoryMessage] = Field(default_factory=list, max_length=10)


class AgentSearchResult(BaseModel):
    rank: int
    bookmark_id: int
    title: str
    url: str


class AgentStructuredMemory(BaseModel):
    last_search_results: list[AgentSearchResult] = Field(default_factory=list)
    selected_bookmark_ids: list[int] = Field(default_factory=list)
    last_tool: Optional[str] = None


class AgentMemory(BaseModel):
    content: AgentContentMemory = Field(default_factory=AgentContentMemory)
    structured: AgentStructuredMemory = Field(default_factory=AgentStructuredMemory)

    @model_validator(mode="before")
    @classmethod
    def migrate_flat_memory(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if "content" in value or "structured" in value:
            return value
        if "last_search_results" in value or "selected_bookmark_ids" in value:
            return {
                "content": {"messages": value.get("messages", [])},
                "structured": {
                    "last_search_results": value.get("last_search_results", []),
                    "selected_bookmark_ids": value.get("selected_bookmark_ids", []),
                    "last_tool": value.get("last_tool"),
                },
            }
        return value


class AgentPendingAction(BaseModel):
    tool: Literal["CreateNoteTool"]
    bookmark_id: int
    note: str


class AgentChatInput(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[AgentHistoryMessage] = Field(default_factory=list, max_length=10)
    memory: AgentMemory = Field(default_factory=AgentMemory)
    confirm_action: Optional[AgentPendingAction] = None


class AgentToolTrace(BaseModel):
    step: int
    node: str
    tool: str
    arguments: dict[str, Any]
    summary: str


class AgentCitation(BaseModel):
    bookmark_id: int
    title: str
    url: str
    excerpt: Optional[str] = None


class AgentChatOut(BaseModel):
    answer: str
    memory: AgentMemory
    trace: list[AgentToolTrace]
    citations: list[AgentCitation]
    pending_action: Optional[AgentPendingAction] = None
    mode: Literal["agent", "confirmed_action", "fallback"]
