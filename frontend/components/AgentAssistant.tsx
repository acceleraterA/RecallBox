"use client";

import { FormEvent, useState } from "react";

import { askAgent } from "@/lib/api";
import type { AgentChatResponse, AgentHistoryMessage, AgentMemory, AgentPendingAction } from "@/lib/types";

type AgentTurn = {
  question: string;
  response: AgentChatResponse;
};

const examples = [
  "Find my Kafka rebalance bookmarks",
  "What does the second one talk about?",
  "What collections or tags do I have?",
  "Create a note from the first result",
];

export function AgentAssistant() {
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<AgentHistoryMessage[]>([]);
  const [memory, setMemory] = useState<AgentMemory>({
    content: { messages: [] },
    structured: {
      last_search_results: [],
      selected_bookmark_ids: [],
      last_tool: null,
    },
  });
  const [turns, setTurns] = useState<AgentTurn[]>([]);
  const [pendingAction, setPendingAction] = useState<AgentPendingAction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(nextMessage: string, confirmAction?: AgentPendingAction) {
    const cleanMessage = nextMessage.trim();
    if (!cleanMessage && !confirmAction) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await askAgent({
        message: cleanMessage || "Confirm action",
        history,
        memory,
        confirm_action: confirmAction,
      });
      setMemory(response.memory);
      setPendingAction(response.pending_action);
      setHistory(response.memory.content.messages);
      if (!confirmAction) {
        setTurns([{ question: cleanMessage, response }, ...turns].slice(0, 4));
      } else {
        setTurns([{ question: "Confirmed action", response }, ...turns].slice(0, 4));
      }
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent request failed");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    send(message);
  }

  return (
    <section className="agent-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">V3 agent demo</p>
          <h2>Ask the tool-calling agent</h2>
        </div>
        <p className="agent-memory">
          Content memory: {memory.content.messages.length} message(s). Structured memory: {memory.structured.selected_bookmark_ids.length} selected.
        </p>
      </div>

      <div className="agent-examples">
        {examples.map((example) => (
          <button key={example} type="button" onClick={() => setMessage(example)}>
            {example}
          </button>
        ))}
      </div>

      <form className="agent-form" onSubmit={handleSubmit}>
        <label className="field grow">
          <span>Message</span>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask it to search bookmarks, inspect a result, list collections, or draft a note."
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Thinking..." : "Ask"}
        </button>
      </form>

      {error ? <p className="error-box">{error}</p> : null}

      {pendingAction ? (
        <div className="pending-action">
          <div>
            <strong>Confirm note creation?</strong>
            <p>{pendingAction.note}</p>
          </div>
          <button type="button" disabled={loading} onClick={() => send("", pendingAction)}>
            Save note
          </button>
        </div>
      ) : null}

      <div className="agent-thread">
        {turns.map((turn, index) => (
          <article className="agent-turn" key={`${turn.question}-${index}`}>
            <p className="agent-question">{turn.question}</p>
            <div className="agent-answer">
              {turn.response.answer.split("\n").map((line, lineIndex) => (
                <p key={lineIndex}>{line || "\u00a0"}</p>
              ))}
            </div>

            {turn.response.trace.length ? (
              <div className="agent-trace">
                {turn.response.trace.map((step) => (
                  <span key={`${step.step}-${step.tool}`}>
                    {step.step}. {step.node} to {step.tool}: {step.summary}
                  </span>
                ))}
              </div>
            ) : null}

            {turn.response.citations.length ? (
              <div className="rag-citations">
                {turn.response.citations.map((citation) => (
                  <a className="rag-citation" href={citation.url} key={citation.bookmark_id} target="_blank">
                    <span>{citation.title}</span>
                    {citation.excerpt ? <small>{citation.excerpt}</small> : null}
                  </a>
                ))}
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
