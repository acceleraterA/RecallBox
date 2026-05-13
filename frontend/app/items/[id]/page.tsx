"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { TagEditor } from "@/components/TagEditor";
import { deleteItem, getItem, updateItem } from "@/lib/api";
import type { Item } from "@/lib/types";

export default function ItemDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);
  const [item, setItem] = useState<Item | null>(null);
  const [note, setNote] = useState("");
  const [tags, setTags] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadItem() {
      setLoading(true);
      setError(null);
      try {
        const data = await getItem(id);
        setItem(data);
        setNote(data.note ?? "");
        setTags(data.tags.join(", "));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load item");
      } finally {
        setLoading(false);
      }
    }

    if (Number.isFinite(id)) {
      loadItem();
    }
  }, [id]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const nextTags = tags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const updated = await updateItem(id, { note, tags: nextTags });
      setItem(updated);
      setNote(updated.note ?? "");
      setTags(updated.tags.join(", "));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update item");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setSaving(true);
    setError(null);
    try {
      await deleteItem(id);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete item");
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="shell narrow">
        <p className="muted">Loading item...</p>
      </main>
    );
  }

  if (!item) {
    return (
      <main className="shell narrow">
        <Link className="back-link" href="/">
          Back
        </Link>
        <p className="error-box">{error ?? "Item not found"}</p>
      </main>
    );
  }

  return (
    <main className="shell narrow">
      <Link className="back-link" href="/">
        Back
      </Link>

      <article className="detail">
        {item.thumbnail_url ? <img className="detail-image" src={item.thumbnail_url} alt="" /> : null}
        <div className="item-meta">
          <span className="platform">{item.platform}</span>
          <span>{item.status}</span>
        </div>
        <h1>{item.title || item.url}</h1>
        <a className="source-link" href={item.url} target="_blank" rel="noreferrer">
          Open original
        </a>
        {item.description ? <p className="lead">{item.description}</p> : null}
        {item.summary ? <p>{item.summary}</p> : null}
        {item.status === "failed" ? (
          <p className="error-box">Metadata extraction failed, but the URL was saved.</p>
        ) : null}
      </article>

      <form className="panel edit-form" onSubmit={handleSave}>
        <label className="field">
          <span>Note</span>
          <textarea value={note} onChange={(event) => setNote(event.target.value)} />
        </label>
        <TagEditor value={tags} onChange={setTags} />
        {error ? <p className="error-text">{error}</p> : null}
        <div className="actions">
          <button className="primary-button" disabled={saving} type="submit">
            {saving ? "Saving..." : "Save changes"}
          </button>
          <button className="danger-button" disabled={saving} type="button" onClick={handleDelete}>
            Delete
          </button>
        </div>
      </form>
    </main>
  );
}
