"use client";

import { FormEvent, useState } from "react";

import { askRecallBox } from "@/lib/api";
import type { RagAnswer, RagHistoryMessage } from "@/lib/types";

type Turn = {
  question: string;
  response: RagAnswer;
};

export function RagAssistant() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuestion = question.trim();
    if (!nextQuestion || loading) {
      return;
    }

    const history: RagHistoryMessage[] = turns.slice(-3).flatMap((turn) => [
      { role: "user", content: turn.question },
      { role: "assistant", content: turn.response.answer },
    ]);

    setLoading(true);
    setError(null);
    try {
      const response = await askRecallBox({ question: nextQuestion, history });
      setTurns((current) => [...current, { question: nextQuestion, response }]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not answer this question");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rag-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Grounded Q&amp;A</p>
          <h2>Ask RecallBox</h2>
        </div>
        {turns.length ? (
          <button className="ghost-button" type="button" onClick={() => setTurns([])}>
            Clear
          </button>
        ) : null}
      </div>

      <form className="rag-form" onSubmit={handleSubmit}>
        <label className="field grow">
          <span>Question</span>
          <textarea
            value={question}
            placeholder="What do my saved links say about Kafka rebalancing?"
            onChange={(event) => setQuestion(event.target.value)}
          />
        </label>
        <button className="primary-button" disabled={loading || !question.trim()} type="submit">
          {loading ? "Thinking..." : "Ask"}
        </button>
      </form>

      {error ? <p className="error-box">{error}</p> : null}

      {turns.length ? (
        <div className="rag-thread">
          {turns.map((turn, turnIndex) => (
            <article className="rag-turn" key={`${turn.question}-${turnIndex}`}>
              <p className="rag-question">{turn.question}</p>
              <div className="rag-answer">
                {turn.response.answer.split("\n").map((line, lineIndex) => (
                  <p key={`${line}-${lineIndex}`}>{line || "\u00a0"}</p>
                ))}
              </div>
              {turn.response.citations.length ? (
                <div className="rag-citations">
                  {turn.response.citations.map((citation, citationIndex) => (
                    <a
                      className="rag-citation"
                      href={citation.url}
                      key={`${citation.item_id}-${citation.chunk_index}`}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <span>[{citationIndex + 1}] {citation.title}</span>
                      <small>{citation.excerpt}</small>
                    </a>
                  ))}
                </div>
              ) : null}
              <p className="rag-mode">
                {turn.response.mode === "llm"
                  ? turn.response.model ?? "LLM answer"
                  : turn.response.mode === "retrieval_only"
                    ? "Retrieval-only fallback"
                    : "No matching context"}
              </p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
