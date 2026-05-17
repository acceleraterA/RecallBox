"use client";

import { FormEvent, useState } from "react";

import type { ItemFilters } from "@/lib/types";

type Props = {
  filters: ItemFilters;
  tags: string[];
  onChange: (filters: ItemFilters) => void;
};

const platforms = [
  "",
  "web",
  "youtube",
  "bilibili",
  "xiaohongshu",
  "douyin",
  "wechat_article",
  "weibo",
  "douban",
  "instagram",
  "snapchat",
  "tiktok",
  "x",
  "medium",
  "reddit",
];

export function SearchFilters({ filters, tags, onChange }: Props) {
  const [q, setQ] = useState(filters.q ?? "");
  const [platform, setPlatform] = useState(filters.platform ?? "");
  const [tag, setTag] = useState(filters.tag ?? "");
  const [dateFrom, setDateFrom] = useState(filters.date_from ?? "");
  const [dateTo, setDateTo] = useState(filters.date_to ?? "");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onChange({
      q: q.trim(),
      platform,
      tag: tag.trim(),
      date_from: dateFrom,
      date_to: dateTo,
    });
  }

  function clearFilters() {
    setQ("");
    setPlatform("");
    setTag("");
    setDateFrom("");
    setDateTo("");
    onChange({});
  }

  return (
    <form className="filters" onSubmit={handleSubmit}>
      <label className="field grow">
        <span>Search</span>
        <input
          value={q}
          placeholder="Search title, notes, URL, description, tags"
          onChange={(event) => setQ(event.target.value)}
        />
      </label>
      <label className="field compact">
        <span>Platform</span>
        <select value={platform} onChange={(event) => setPlatform(event.target.value)}>
          {platforms.map((value) => (
            <option key={value || "all"} value={value}>
              {value || "All"}
            </option>
          ))}
        </select>
      </label>
      <label className="field compact">
        <span>Tag</span>
        <select value={tag} onChange={(event) => setTag(event.target.value)}>
          <option value="">All</option>
          {tags.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </label>
      <label className="field compact">
        <span>From</span>
        <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
      </label>
      <label className="field compact">
        <span>To</span>
        <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
      </label>
      <button className="secondary-button" type="submit">
        Apply
      </button>
      <button className="ghost-button" type="button" onClick={clearFilters}>
        Clear
      </button>
    </form>
  );
}
