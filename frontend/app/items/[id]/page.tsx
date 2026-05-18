"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AuthPanel } from "@/components/AuthPanel";
import { TagEditor } from "@/components/TagEditor";
import { deleteItem, getItem, updateItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Item } from "@/lib/types";

export default function ItemDetailPage() {
  const { authReady, isAuthEnabled, session } = useAuth();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);
  const [item, setItem] = useState<Item | null>(null);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [thumbnailUrl, setThumbnailUrl] = useState("");
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
        setTitle(data.title ?? "");
        setNote(data.note ?? "");
        setThumbnailUrl(data.thumbnail_url ?? "");
        setTags(data.tags.join(", "));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load item");
      } finally {
        setLoading(false);
      }
    }

    if (!authReady) {
      return;
    }

    if (isAuthEnabled && !session) {
      setItem(null);
      setLoading(false);
      return;
    }

    if (Number.isFinite(id)) {
      loadItem();
    }
  }, [authReady, id, isAuthEnabled, session]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const nextTags = tags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const updated = await updateItem(id, {
        title: title.trim() || null,
        note,
        thumbnail_url: thumbnailUrl.trim() || null,
        tags: nextTags,
      });
      setItem(updated);
      setTitle(updated.title ?? "");
      setNote(updated.note ?? "");
      setThumbnailUrl(updated.thumbnail_url ?? "");
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

  if (!authReady || loading) {
    return (
      <main className="shell narrow">
        <p className="muted">{!authReady ? "Checking account..." : "Loading item..."}</p>
      </main>
    );
  }

  if (isAuthEnabled && !session) {
    return (
      <main className="shell narrow">
        <Link className="back-link" href="/">
          Back
        </Link>
        <AuthPanel />
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
          <p className="error-box">Preview unavailable, but the URL was saved.</p>
        ) : null}
      </article>

      <form className="panel edit-form" onSubmit={handleSave}>
        <label className="field">
          <span>Title</span>
          <input
            value={title}
            placeholder="Add a clearer title"
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label className="field">
          <span>Note</span>
          <textarea value={note} onChange={(event) => setNote(event.target.value)} />
        </label>
        <label className="field">
          <span>Thumbnail URL</span>
          <input
            type="url"
            value={thumbnailUrl}
            placeholder="https://example.com/image.jpg"
            onChange={(event) => setThumbnailUrl(event.target.value)}
          />
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
