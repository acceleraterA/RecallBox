from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, TypedDict

from huggingface_hub import InferenceClient
from langgraph.graph import END, START, StateGraph
import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.agent.schemas import (
    AgentChatOut,
    AgentCitation,
    AgentContentMemory,
    AgentHistoryMessage,
    AgentMemory,
    AgentPendingAction,
    AgentSearchResult,
    AgentStructuredMemory,
    AgentToolTrace,
)
from app.agent.tools import (
    ToolContext,
    create_note_tool,
    get_bookmark_content_tool,
    list_collections_tool,
    search_bookmarks_tool,
)

logger = logging.getLogger(__name__)
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
MAX_REACT_STEPS = 4
ALLOWED_TOOLS = {
    "SearchBookmarksTool",
    "GetBookmarkContentTool",
    "ListCollectionsTool",
    "CreateNoteTool",
}
ORDINALS = {
    "first": 1,
    "1st": 1,
    "第一个": 1,
    "第1个": 1,
    "second": 2,
    "2nd": 2,
    "第二个": 2,
    "第2个": 2,
    "third": 3,
    "3rd": 3,
    "第三个": 3,
    "第3个": 3,
}


class AgentGraphState(TypedDict, total=False):
    db: Session
    user_id: int
    message: str
    confirm_action: Optional[AgentPendingAction]
    content_memory: AgentContentMemory
    structured_memory: AgentStructuredMemory
    current_action: dict[str, Any]
    current_observation: dict[str, Any]
    scratchpad: list[dict[str, Any]]
    tool_result: dict[str, Any]
    answer: str
    citations: list[AgentCitation]
    pending_action: Optional[AgentPendingAction]
    trace: list[AgentToolTrace]
    mode: str
    step_count: int
    max_steps: int


def _trace(state: AgentGraphState, node: str, tool: str, arguments: dict[str, Any], summary: str) -> AgentGraphState:
    trace = list(state.get("trace", []))
    trace.append(
        AgentToolTrace(
            step=len(trace) + 1,
            node=node,
            tool=tool,
            arguments=arguments,
            summary=summary,
        )
    )
    return {"trace": trace}


def _extract_json_object(content: str) -> Optional[dict[str, Any]]:
    content = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fenced:
        content = fenced.group(1)
    else:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        content = content[start : end + 1]
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _chat_text(messages: list[dict[str, str]], *, max_tokens: int = 260) -> Optional[str]:
    if not settings.enable_llm:
        return None

    if settings.llm_provider == "huggingface":
        if not settings.huggingface_token:
            return None
        try:
            client = InferenceClient(provider="auto", api_key=settings.huggingface_token)
            response = client.chat_completion(
                messages,
                model=settings.huggingface_chat_model,
                max_tokens=max_tokens,
                temperature=0,
                extra_body=(
                    {"reasoning_effort": "low"}
                    if settings.huggingface_chat_model.startswith("openai/gpt-oss-")
                    else None
                ),
            )
            content = response.choices[0].message.content
            return content if isinstance(content, str) else None
        except Exception as exc:
            logger.warning("Agent Hugging Face reason step failed: %s", exc)
            return None

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            return None
        try:
            response = requests.post(
                OPENAI_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_chat_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0,
                },
                timeout=25,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("Agent OpenAI reason step failed: %s", exc)
            return None

    return None


def _resolve_referenced_bookmark_id(message: str, structured_memory: AgentStructuredMemory) -> Optional[int]:
    lowered = message.lower()
    for token, rank in ORDINALS.items():
        if token in lowered or token in message:
            index = rank - 1
            if 0 <= index < len(structured_memory.last_search_results):
                return structured_memory.last_search_results[index].bookmark_id

    match = re.search(r"\bbookmark\s*(\d+)\b", lowered)
    if match:
        return int(match.group(1))

    if len(structured_memory.selected_bookmark_ids) == 1:
        return structured_memory.selected_bookmark_ids[0]
    return None


def _looks_like_collection_request(message: str) -> bool:
    lowered = message.lower()
    return any(word in lowered for word in ["collection", "collections", "tag", "tags", "platform", "topic", "topics"]) or any(
        word in message for word in ["分类", "标签", "平台", "主题", "收藏夹"]
    )


def _looks_like_note_request(message: str) -> bool:
    lowered = message.lower()
    return any(word in lowered for word in ["note", "save this", "write down", "remember this"]) or any(
        word in message for word in ["笔记", "记录", "记下来", "保存总结"]
    )


def _looks_like_content_request(message: str) -> bool:
    lowered = message.lower()
    return any(word in lowered for word in ["why", "how", "what", "summarize", "explain", "tell me about"]) or any(
        word in message for word in ["为什么", "怎么", "总结", "解释", "讲了什么", "是什么"]
    )


def _citations_from_passages(passages: list[dict[str, Any]]) -> list[AgentCitation]:
    seen: set[int] = set()
    citations: list[AgentCitation] = []
    for passage in passages:
        bookmark_id = int(passage["bookmark_id"])
        if bookmark_id in seen:
            continue
        seen.add(bookmark_id)
        citations.append(
            AgentCitation(
                bookmark_id=bookmark_id,
                title=passage["title"],
                url=passage["url"],
                excerpt=passage.get("excerpt"),
            )
        )
    return citations


def _answer_from_search(result: dict[str, Any]) -> str:
    bookmarks = result.get("bookmarks", [])
    if not bookmarks:
        return "I could not find matching bookmarks. Try a more specific keyword or save a source first."
    lines = [f"I found {len(bookmarks)} bookmark(s) using {result.get('mode', 'search')} search:"]
    for bookmark in bookmarks:
        tags = ", ".join(bookmark.get("tags", []))
        suffix = f" ({tags})" if tags else ""
        lines.append(f"{bookmark['rank']}. {bookmark['title']}{suffix}\n   {bookmark['url']}")
    return "\n".join(lines)


def _answer_from_passages(message: str, passages: list[dict[str, Any]]) -> str:
    if not passages:
        return "I found bookmarks, but I could not find indexed content for them yet. Run the RAG backfill or open/save the links again to index content."
    lines = [message.strip(), ""]
    for index, passage in enumerate(passages[:4], start=1):
        lines.append(f"[{index}] {passage['title']}")
        lines.append(passage["excerpt"])
        lines.append("")
    lines.append("These passages come from your saved bookmarks; use the citations below to open the sources.")
    return "\n".join(lines).strip()


def _note_from_passages(passages: list[dict[str, Any]]) -> str:
    if not passages:
        return "Review this bookmark later."
    first = passages[0]
    excerpt = first.get("excerpt") or ""
    return f"{first['title']}: {' '.join(excerpt.split())[:420]}"


def _search_memory(result: dict[str, Any], *, last_tool: str) -> AgentStructuredMemory:
    search_results = [
        AgentSearchResult(
            rank=bookmark["rank"],
            bookmark_id=bookmark["bookmark_id"],
            title=bookmark["title"],
            url=bookmark["url"],
        )
        for bookmark in result.get("bookmarks", [])
    ]
    return AgentStructuredMemory(
        last_search_results=search_results,
        selected_bookmark_ids=[entry.bookmark_id for entry in search_results],
        last_tool=last_tool,
    )


def _observation_summary(tool: str, result: dict[str, Any]) -> str:
    if tool == "SearchBookmarksTool":
        titles = [bookmark["title"] for bookmark in result.get("bookmarks", [])[:3]]
        return f"Found {len(result.get('bookmarks', []))} bookmarks: {', '.join(titles) or 'none'}"
    if tool == "GetBookmarkContentTool":
        return f"Loaded {len(result.get('passages', []))} passages"
    if tool == "ListCollectionsTool":
        return f"Listed {len(result.get('tags', []))} tags and {len(result.get('platforms', []))} platforms"
    return "Tool executed"


def _final_from_scratchpad(state: AgentGraphState) -> str:
    result = state.get("tool_result", {})
    tool = state.get("current_action", {}).get("tool") or state.get("structured_memory", AgentStructuredMemory()).last_tool
    if tool == "SearchBookmarksTool":
        return _answer_from_search(result)
    if tool == "ListCollectionsTool":
        tags = ", ".join(result.get("tags", [])) or "no tags yet"
        platforms = ", ".join(result.get("platforms", [])) or "no platforms yet"
        return f"Current tags: {tags}\nCurrent platforms: {platforms}"
    if tool == "GetBookmarkContentTool":
        return _answer_from_passages(state["message"], result.get("passages", []))
    if state.get("scratchpad"):
        return state["scratchpad"][-1].get("observation", "I completed the tool call.")
    return "I could not complete that request. Try a more specific question."


def _llm_reason_action(state: AgentGraphState) -> Optional[dict[str, Any]]:
    content_memory = state["content_memory"]
    structured_memory = state["structured_memory"]
    memory_summary = {
        "content_messages": [message.model_dump() for message in content_memory.messages[-6:]],
        "last_search_results": [entry.model_dump() for entry in structured_memory.last_search_results[:5]],
        "selected_bookmark_ids": structured_memory.selected_bookmark_ids[:5],
        "last_tool": structured_memory.last_tool,
    }
    tool_spec = {
        "SearchBookmarksTool": {"query": "string", "semantic": "boolean", "platform": "string|null", "tag": "string|null", "limit": "number"},
        "GetBookmarkContentTool": {"bookmark_ids": "number[]|null", "query": "string|null", "top_k": "number"},
        "ListCollectionsTool": {},
        "CreateNoteTool": {"bookmark_id": "number", "note": "string"},
    }
    content = _chat_text(
        [
            {
                "role": "system",
                "content": (
                    "You are a RecallBox ReAct agent. Return JSON only. "
                    "Choose either {\"type\": \"tool_call\", \"tool\": string, \"arguments\": object, \"reason_summary\": string} "
                    "or {\"type\": \"final_answer\", \"answer\": string, \"reason_summary\": string}. "
                    "Use observations in the scratchpad before deciding the next step. "
                    "Use read tools freely. Use CreateNoteTool only when the user wants a note; it requires confirmation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Tools: {json.dumps(tool_spec)}\n"
                    f"Content memory and structured memory: {json.dumps(memory_summary)}\n"
                    f"Scratchpad observations: {json.dumps(state.get('scratchpad', [])[-4:])}\n"
                    f"User message: {state['message']}"
                ),
            },
        ]
    )
    if not content:
        return None
    action = _extract_json_object(content)
    if not isinstance(action, dict):
        return None
    action_type = action.get("type")
    if action_type == "final_answer" and isinstance(action.get("answer"), str):
        return {"type": "final_answer", "answer": action["answer"], "source": "llm", "reason_summary": action.get("reason_summary", "LLM chose to answer")}
    if action_type == "tool_call" and action.get("tool") in ALLOWED_TOOLS and isinstance(action.get("arguments"), dict):
        return {
            "type": "tool_call",
            "tool": action["tool"],
            "arguments": action["arguments"],
            "source": "llm",
            "reason_summary": action.get("reason_summary", "LLM chose a tool"),
        }
    return None


def _heuristic_reason_action(state: AgentGraphState) -> dict[str, Any]:
    message = state["message"]
    scratchpad = state.get("scratchpad", [])
    structured = state["structured_memory"]
    referenced_id = _resolve_referenced_bookmark_id(message, structured)

    if not scratchpad:
        if _looks_like_collection_request(message):
            return {"type": "tool_call", "tool": "ListCollectionsTool", "arguments": {}, "source": "heuristic", "reason_summary": "User asks about collections"}
        if _looks_like_note_request(message) and referenced_id:
            return {"type": "tool_call", "tool": "CreateNoteTool", "arguments": {"bookmark_id": referenced_id, "note": ""}, "source": "heuristic", "reason_summary": "User asks to create a note from a referenced bookmark"}
        if referenced_id:
            return {"type": "tool_call", "tool": "GetBookmarkContentTool", "arguments": {"bookmark_ids": [referenced_id], "query": message, "top_k": 4}, "source": "heuristic", "reason_summary": "User refers to a selected bookmark"}
        return {"type": "tool_call", "tool": "SearchBookmarksTool", "arguments": {"query": message, "semantic": True, "limit": 5}, "source": "heuristic", "reason_summary": "Start with bookmark search"}

    last_action = scratchpad[-1].get("tool")
    result = state.get("tool_result", {})
    if last_action == "SearchBookmarksTool":
        bookmarks = result.get("bookmarks", [])
        if not bookmarks:
            return {"type": "final_answer", "answer": _answer_from_search(result), "source": "heuristic", "reason_summary": "Search returned no bookmarks"}
        if _looks_like_content_request(message) or _looks_like_note_request(message):
            bookmark_ids = [bookmark["bookmark_id"] for bookmark in bookmarks[:3]]
            return {"type": "tool_call", "tool": "GetBookmarkContentTool", "arguments": {"bookmark_ids": bookmark_ids, "query": message, "top_k": 2}, "source": "heuristic", "reason_summary": "Need content after search observation"}
        return {"type": "final_answer", "answer": _answer_from_search(result), "source": "heuristic", "reason_summary": "Search results are enough"}

    if last_action == "GetBookmarkContentTool":
        if _looks_like_note_request(message):
            citations = state.get("citations", [])
            bookmark_id = citations[0].bookmark_id if citations else (structured.selected_bookmark_ids[0] if structured.selected_bookmark_ids else None)
            if bookmark_id:
                return {"type": "tool_call", "tool": "CreateNoteTool", "arguments": {"bookmark_id": bookmark_id, "note": _note_from_passages(result.get("passages", []))}, "source": "heuristic", "reason_summary": "User wants a note after reading content"}
        return {"type": "final_answer", "answer": _answer_from_passages(message, result.get("passages", [])), "source": "heuristic", "reason_summary": "Content observation is enough"}

    if last_action == "ListCollectionsTool":
        return {"type": "final_answer", "answer": _final_from_scratchpad(state), "source": "heuristic", "reason_summary": "Collection list is enough"}

    return {"type": "final_answer", "answer": _final_from_scratchpad(state), "source": "heuristic", "reason_summary": "Stop with best available observation"}


def _start_route(state: AgentGraphState) -> str:
    return "confirm_action" if state.get("confirm_action") else "reason"


def confirm_action_node(state: AgentGraphState) -> AgentGraphState:
    action = state["confirm_action"]
    context = ToolContext(db=state["db"], user_id=state["user_id"])
    result = create_note_tool(context, bookmark_id=action.bookmark_id, note=action.note, confirmed=True)
    update = _trace(state, "confirm_action", "CreateNoteTool", {"bookmark_id": action.bookmark_id, "confirmed": True}, result["status"])
    update.update(
        {
            "answer": f"Saved the note to bookmark {action.bookmark_id}.",
            "mode": "confirmed_action",
            "pending_action": None,
            "citations": [],
        }
    )
    return update


def reason_node(state: AgentGraphState) -> AgentGraphState:
    if state.get("step_count", 0) >= state.get("max_steps", MAX_REACT_STEPS):
        return {"current_action": {"type": "final_answer", "answer": _final_from_scratchpad(state), "source": "max_steps", "reason_summary": "Reached max ReAct steps"}}
    action = _llm_reason_action(state) or _heuristic_reason_action(state)
    update = _trace(
        state,
        "reason",
        action.get("tool") or action.get("type", "final_answer"),
        action.get("arguments", {}),
        action.get("reason_summary", f"selected by {action.get('source', 'agent')}"),
    )
    update["current_action"] = action
    return update


def _after_reason(state: AgentGraphState) -> str:
    return "final" if state.get("current_action", {}).get("type") == "final_answer" else "guardrail"


def guardrail_node(state: AgentGraphState) -> AgentGraphState:
    action = state["current_action"]
    tool = action.get("tool")
    arguments = dict(action.get("arguments", {}))
    if tool not in ALLOWED_TOOLS:
        update = _trace(state, "guardrail", str(tool), arguments, "blocked: tool is not allowlisted")
        update.update({"answer": "I cannot use that tool.", "mode": "fallback"})
        return update

    if state.get("step_count", 0) >= state.get("max_steps", MAX_REACT_STEPS):
        update = _trace(state, "guardrail", tool, arguments, "blocked: max steps reached")
        update.update({"answer": _final_from_scratchpad(state), "mode": "fallback"})
        return update

    if tool == "CreateNoteTool":
        context = ToolContext(db=state["db"], user_id=state["user_id"])
        bookmark_id = arguments.get("bookmark_id") or _resolve_referenced_bookmark_id(state["message"], state["structured_memory"])
        if not bookmark_id:
            update = _trace(state, "guardrail", tool, arguments, "blocked: no bookmark selected")
            update.update({"answer": "Please choose a bookmark before I create a note.", "mode": "fallback"})
            return update

        note = str(arguments.get("note") or "").strip()
        if not note or note == state["message"].strip():
            content_result = get_bookmark_content_tool(context, bookmark_ids=[int(bookmark_id)], query=state["message"], top_k=2)
            note = _note_from_passages(content_result["passages"])
        result = create_note_tool(context, bookmark_id=int(bookmark_id), note=note, confirmed=False)
        if result.get("status") != "needs_confirmation":
            update = _trace(state, "guardrail", tool, arguments, result.get("status", "blocked"))
            update.update({"answer": "I could not create a note for that bookmark.", "mode": "fallback"})
            return update

        pending = AgentPendingAction(tool="CreateNoteTool", bookmark_id=int(bookmark_id), note=result["note"])
        update = _trace(state, "guardrail", tool, {"bookmark_id": int(bookmark_id), "confirmed": False}, "write action requires user confirmation")
        update.update(
            {
                "answer": f"I drafted a note for bookmark {bookmark_id}. Confirm before I save it.",
                "pending_action": pending,
                "mode": "agent",
            }
        )
        return update

    return _trace(state, "guardrail", tool, arguments, "allowed")


def _after_guardrail(state: AgentGraphState) -> str:
    return "final" if state.get("answer") or state.get("pending_action") else "act"


def act_node(state: AgentGraphState) -> AgentGraphState:
    context = ToolContext(db=state["db"], user_id=state["user_id"])
    action = state["current_action"]
    tool = action["tool"]
    arguments = dict(action.get("arguments", {}))

    if tool == "SearchBookmarksTool":
        result = search_bookmarks_tool(
            context,
            query=str(arguments.get("query") or state["message"]),
            semantic=bool(arguments.get("semantic", True)),
            platform=arguments.get("platform"),
            tag=arguments.get("tag"),
            limit=int(arguments.get("limit") or 5),
        )
    elif tool == "GetBookmarkContentTool":
        bookmark_ids = arguments.get("bookmark_ids")
        if bookmark_ids is not None and not isinstance(bookmark_ids, list):
            bookmark_ids = None
        result = get_bookmark_content_tool(
            context,
            bookmark_ids=bookmark_ids,
            query=arguments.get("query") or state["message"],
            top_k=int(arguments.get("top_k") or 5),
        )
    elif tool == "ListCollectionsTool":
        result = list_collections_tool(context)
    else:
        result = {}

    update = _trace(state, "act", tool, arguments, _observation_summary(tool, result))
    update["tool_result"] = result
    return update


def observe_node(state: AgentGraphState) -> AgentGraphState:
    action = state["current_action"]
    tool = action["tool"]
    result = state.get("tool_result", {})
    structured = state["structured_memory"]
    citations = state.get("citations", [])

    if tool == "SearchBookmarksTool":
        structured = _search_memory(result, last_tool=tool)
        citations = [
            AgentCitation(bookmark_id=bookmark["bookmark_id"], title=bookmark["title"], url=bookmark["url"])
            for bookmark in result.get("bookmarks", [])
        ]
    elif tool == "GetBookmarkContentTool":
        citations = _citations_from_passages(result.get("passages", []))
        structured = AgentStructuredMemory(
            last_search_results=structured.last_search_results,
            selected_bookmark_ids=[citation.bookmark_id for citation in citations] or structured.selected_bookmark_ids,
            last_tool=tool,
        )
    elif tool == "ListCollectionsTool":
        structured = AgentStructuredMemory(
            last_search_results=structured.last_search_results,
            selected_bookmark_ids=structured.selected_bookmark_ids,
            last_tool=tool,
        )

    observation = {
        "tool": tool,
        "summary": _observation_summary(tool, result),
        "result": result,
    }
    scratchpad = [
        *state.get("scratchpad", []),
        {
            "reason": action.get("reason_summary", "selected tool"),
            "tool": tool,
            "arguments": action.get("arguments", {}),
            "observation": observation["summary"],
        },
    ][-state.get("max_steps", MAX_REACT_STEPS) :]
    update = _trace(state, "observe", tool, {}, observation["summary"])
    update.update(
        {
            "current_observation": observation,
            "structured_memory": structured,
            "citations": citations,
            "scratchpad": scratchpad,
            "step_count": state.get("step_count", 0) + 1,
        }
    )
    return update


def _after_observe(state: AgentGraphState) -> str:
    return "final" if state.get("step_count", 0) >= state.get("max_steps", MAX_REACT_STEPS) else "reason"


def final_node(state: AgentGraphState) -> AgentGraphState:
    action = state.get("current_action", {})
    if state.get("answer"):
        answer = state["answer"]
    elif action.get("type") == "final_answer":
        answer = action.get("answer") or _final_from_scratchpad(state)
    else:
        answer = _final_from_scratchpad(state)

    next_messages = [
        *state["content_memory"].messages,
        AgentHistoryMessage(role="user", content=state["message"]),
        AgentHistoryMessage(role="assistant", content=answer),
    ][-10:]
    return {
        "answer": answer,
        "content_memory": AgentContentMemory(messages=next_messages),
        "citations": state.get("citations", []),
        "mode": state.get("mode", "agent"),
    }


def build_agent_graph():
    graph = StateGraph(AgentGraphState)
    graph.add_node("confirm_action", confirm_action_node)
    graph.add_node("reason", reason_node)
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("act", act_node)
    graph.add_node("observe", observe_node)
    graph.add_node("final", final_node)

    graph.add_conditional_edges(START, _start_route, {"confirm_action": "confirm_action", "reason": "reason"})
    graph.add_edge("confirm_action", "final")
    graph.add_conditional_edges("reason", _after_reason, {"guardrail": "guardrail", "final": "final"})
    graph.add_conditional_edges("guardrail", _after_guardrail, {"act": "act", "final": "final"})
    graph.add_edge("act", "observe")
    graph.add_conditional_edges("observe", _after_observe, {"reason": "reason", "final": "final"})
    graph.add_edge("final", END)
    return graph.compile()


AGENT_GRAPH = build_agent_graph()


def run_agent_graph(
    *,
    db: Session,
    user_id: int,
    message: str,
    content_memory: AgentContentMemory,
    structured_memory: AgentStructuredMemory,
    confirm_action: Optional[AgentPendingAction],
) -> AgentChatOut:
    final_state = AGENT_GRAPH.invoke(
        {
            "db": db,
            "user_id": user_id,
            "message": message,
            "confirm_action": confirm_action,
            "content_memory": content_memory,
            "structured_memory": structured_memory,
            "trace": [],
            "citations": [],
            "pending_action": None,
            "scratchpad": [],
            "step_count": 0,
            "max_steps": MAX_REACT_STEPS,
            "mode": "agent",
        }
    )
    return AgentChatOut(
        answer=final_state["answer"],
        memory=AgentMemory(
            content=final_state["content_memory"],
            structured=final_state.get("structured_memory", structured_memory),
        ),
        trace=final_state.get("trace", []),
        citations=final_state.get("citations", []),
        pending_action=final_state.get("pending_action"),
        mode=final_state.get("mode", "agent"),
    )
