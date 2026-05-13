import Link from "next/link";

import type { Item } from "@/lib/types";

type Props = {
  item: Item;
};

export function ItemCard({ item }: Props) {
  const displayTitle = item.title || item.url;
  const preview = item.summary || item.description || item.note || "No preview text yet.";
  const createdAt = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(item.created_at));

  return (
    <article className="item-card">
      {item.thumbnail_url ? (
        <img className="item-thumbnail" src={item.thumbnail_url} alt="" loading="lazy" />
      ) : (
        <div className="item-thumbnail placeholder" />
      )}
      <div className="item-content">
        <div className="item-meta">
          <span className="platform">{item.platform}</span>
          <span>{createdAt}</span>
          {item.status === "failed" ? <span className="status failed">metadata failed</span> : null}
        </div>
        <Link className="item-title" href={`/items/${item.id}`}>
          {displayTitle}
        </Link>
        <p className="item-preview">{preview}</p>
        <div className="tag-row">
          {item.tags.length ? item.tags.map((tag) => <span key={tag}>{tag}</span>) : <span>untagged</span>}
        </div>
      </div>
    </article>
  );
}
