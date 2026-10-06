from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.llm import generate_rag_answer
from app.models import User
from app.rag import retrieve_chunks
from app.schemas import RagAnswerOut, RagAskInput, RagCitationOut

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask", response_model=RagAnswerOut)
def ask_recallbox(
    payload: RagAskInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RagAnswerOut:
    question = payload.question.strip()
    history = [message.model_dump() for message in payload.history]
    previous_user_message = next(
        (message["content"] for message in reversed(history) if message["role"] == "user"),
        None,
    )
    retrieval_question = (
        f"Previous question: {previous_user_message}\nFollow-up question: {question}"
        if previous_user_message
        else question
    )
    chunks = retrieve_chunks(
        db,
        user_id=user.id,
        question=retrieval_question,
        top_k=payload.top_k,
    )
    result = generate_rag_answer(
        question=question,
        chunks=chunks,
        history=history,
    )
    citations = [
        RagCitationOut(
            item_id=chunk.item_id,
            title=chunk.title,
            url=chunk.url,
            excerpt=" ".join(chunk.content.split())[:420],
            chunk_index=chunk.chunk_index,
            similarity=round(chunk.similarity, 4),
        )
        for chunk in chunks
    ]
    return RagAnswerOut(
        answer=result.answer,
        citations=citations,
        mode=result.mode,
        model=result.model,
    )
