"use client";

import { useCallback, useEffect, useState } from "react";

import { AddItemForm } from "@/components/AddItemForm";
import { ItemCard } from "@/components/ItemCard";
import { SearchFilters } from "@/components/SearchFilters";
import { createItem, getItems } from "@/lib/api";
import type { Item, ItemFilters } from "@/lib/types";

export default function HomePage() {
  const [items, setItems] = useState<Item[]>([]);
  const [filters, setFilters] = useState<ItemFilters>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadItems = useCallback(async (nextFilters = filters) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getItems({ ...nextFilters, limit: 50, offset: 0 });
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load items");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  async function handleCreate(input: { url: string; note?: string }) {
    await createItem(input);
    await loadItems();
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
      </header>

      <section className="panel">
        <AddItemForm onCreate={handleCreate} />
      </section>

      <section className="list-section">
        <SearchFilters filters={filters} onChange={handleFiltersChange} />

        {error ? <p className="error-box">{error}</p> : null}
        {loading ? <p className="muted">Loading saved links...</p> : null}

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
    </main>
  );
}
