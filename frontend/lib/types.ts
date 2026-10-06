export type Item = {
  id: number;
  url: string;
  platform: string;
  title: string | null;
  description: string | null;
  summary: string | null;
  note: string | null;
  thumbnail_url: string | null;
  content_status: "pending" | "ready" | "partial" | "failed" | string;
  status: "processing" | "ready" | "failed" | string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type ItemFilters = {
  q?: string;
  platform?: string;
  tag?: string;
  date_from?: string;
  date_to?: string;
  semantic?: boolean;
  limit?: number;
  offset?: number;
};

export type CreateItemInput = {
  url: string;
  note?: string;
};

export type UpdateItemInput = {
  title?: string | null;
  note?: string | null;
  thumbnail_url?: string | null;
  tags?: string[];
};

export type RagHistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type RagCitation = {
  item_id: number;
  title: string;
  url: string;
  excerpt: string;
  chunk_index: number;
  similarity: number;
};

export type RagAnswer = {
  answer: string;
  citations: RagCitation[];
  mode: "llm" | "retrieval_only" | "no_context";
  model: string | null;
};

export type RagAskInput = {
  question: string;
  history?: RagHistoryMessage[];
  top_k?: number;
};


export type AgentHistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AgentSearchResult = {
  rank: number;
  bookmark_id: number;
  title: string;
  url: string;
};

export type AgentContentMemory = {
  messages: AgentHistoryMessage[];
};

export type AgentStructuredMemory = {
  last_search_results: AgentSearchResult[];
  selected_bookmark_ids: number[];
  last_tool: string | null;
};

export type AgentMemory = {
  content: AgentContentMemory;
  structured: AgentStructuredMemory;
};

export type AgentPendingAction = {
  tool: "CreateNoteTool";
  bookmark_id: number;
  note: string;
};

export type AgentToolTrace = {
  step: number;
  node: string;
  tool: string;
  arguments: Record<string, unknown>;
  summary: string;
};

export type AgentCitation = {
  bookmark_id: number;
  title: string;
  url: string;
  excerpt: string | null;
};

export type AgentChatInput = {
  message: string;
  history?: AgentHistoryMessage[];
  memory?: AgentMemory;
  confirm_action?: AgentPendingAction | null;
};

export type AgentChatResponse = {
  answer: string;
  memory: AgentMemory;
  trace: AgentToolTrace[];
  citations: AgentCitation[];
  pending_action: AgentPendingAction | null;
  mode: "agent" | "confirmed_action" | "fallback";
};
