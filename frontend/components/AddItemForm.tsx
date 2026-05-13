"use client";

import { FormEvent, useState } from "react";

type Props = {
  onCreate: (input: { url: string; note?: string }) => Promise<void>;
};

export function AddItemForm({ onCreate }: Props) {
  const [url, setUrl] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onCreate({ url, note: note.trim() || undefined });
      setUrl("");
      setNote("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save item");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="add-form" onSubmit={handleSubmit}>
      <div className="field-row">
        <label className="field grow">
          <span>URL or share text</span>
          <input
            required
            type="text"
            value={url}
            placeholder="Paste a URL, Xiaohongshu/Douyin share text, profile, or collection link"
            onChange={(event) => setUrl(event.target.value)}
          />
        </label>
        <button className="primary-button" disabled={submitting} type="submit">
          {submitting ? "Saving..." : "Save"}
        </button>
      </div>
      <label className="field">
        <span>Note</span>
        <textarea
          value={note}
          placeholder="Optional context to help you find this later"
          onChange={(event) => setNote(event.target.value)}
        />
      </label>
      {error ? <p className="error-text">{error}</p> : null}
    </form>
  );
}
