"use client";

import { useCallback, useEffect, useState } from "react";

import { AddItemForm } from "@/components/AddItemForm";
import { AccountBar, AuthPanel } from "@/components/AuthPanel";
import { ItemCard } from "@/components/ItemCard";
import { SearchFilters } from "@/components/SearchFilters";
import { createItem, getItems, getTags } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Item, ItemFilters } from "@/lib/types";

export default function HomePage() {
  const { authReady, isAuthEnabled, session } = useAuth();
  const [items, setItems] = useState<Item[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [filters, setFilters] = useState<ItemFilters>({});
  const [loading, setLoading] = useState(true);
  const [slowLoading, setSlowLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadItems = useCallback(async (nextFilters = filters) => {
    setLoading(true);
    setSlowLoading(false);
    setError(null);
    const slowLoadingTimer = window.setTimeout(() => setSlowLoading(true), 1200);

    try {
      const data = await getItems({ ...nextFilters, limit: 50, offset: 0 });
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load items");
    } finally {
      window.clearTimeout(slowLoadingTimer);
      setSlowLoading(false);
      setLoading(false);
    }
  }, [filters]);

  const loadTags = useCallback(async () => {
    try {
      const data = await getTags();
      setTags(data);
    } catch {
      setTags([]);
    }
  }, []);

  useEffect(() => {
    if (!authReady) {
      return;
    }

    if (isAuthEnabled && !session) {
      setItems([]);
      setTags([]);
      setLoading(false);
      return;
    }

    loadItems();
    loadTags();
  }, [authReady, isAuthEnabled, session, loadItems, loadTags]);

  async function handleCreate(input: { url: string; note?: string }) {
    await createItem(input);
    await loadItems();
    await loadTags();
  }

  function handleFiltersChange(nextFilters: ItemFilters) {
    setFilters(nextFilters);
    loadItems(nextFilters);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">RecallBox</p>
          <h1>Saved links, ready when your memory is not.</h1>
        </div>
        <AccountBar />
      </header>

      {!authReady ? <p className="muted">Checking account...</p> : null}

      {authReady && isAuthEnabled && !session ? <AuthPanel /> : null}

      {authReady && (!isAuthEnabled || session) ? (
        <section className="panel">
          <AddItemForm onCreate={handleCreate} />
        </section>
      ) : null}

      {authReady && (!isAuthEnabled || session) ? (
      <section className="list-section">
        <SearchFilters filters={filters} tags={tags} onChange={handleFiltersChange} />

        {error ? <p className="error-box">{error}</p> : null}
        {loading ? <p className="muted">{slowLoading ? "Waking up RecallBox API..." : "Loading saved links..."}</p> : null}

        {!loading && !error && items.length === 0 ? (
          <div className="empty-state">
            <h2>No saved links yet</h2>
            <p>Paste a URL above to create your first RecallBox item.</p>
          </div>
        ) : null}

        <div className="item-grid">
          {items.map((item) => (
            <ItemCard key={item.id} item={item} />
          ))}
        </div>
      </section>
      ) : null}
    </main>
  );
}
