export type Item = {
  id: number;
  url: string;
  platform: string;
  title: string | null;
  description: string | null;
  summary: string | null;
  note: string | null;
  thumbnail_url: string | null;
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
