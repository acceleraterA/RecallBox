import type { CreateItemInput, Item, ItemFilters, UpdateItemInput } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const API_TIMEOUT_MS = 30000;

function errorMessage(body: unknown): string {
  if (!body || typeof body !== "object") {
    return "Request failed";
  }

  const detail = "detail" in body ? (body as { detail?: unknown }).detail : undefined;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((entry) => {
        if (entry && typeof entry === "object" && "msg" in entry) {
          return String((entry as { msg: unknown }).msg);
        }
        return String(entry);
      })
      .join(", ");
  }
  return "Request failed";
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(
        `RecallBox API at ${API_BASE_URL} took too long to respond. The free backend may still be waking up; refresh in a moment or try again.`,
      );
    }

    throw new Error(
      `Could not reach RecallBox API at ${API_BASE_URL}. Make sure the backend is running and restart the frontend if .env.local changed.`,
    );
  } finally {
    window.clearTimeout(timeout);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(errorMessage(body));
  }

  return body as T;
}

export async function getItems(filters: ItemFilters = {}): Promise<Item[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      params.set(key, String(value));
    }
  }

  const query = params.toString();
  return apiRequest<Item[]>(`/items${query ? `?${query}` : ""}`);
}


export async function getTags(): Promise<string[]> {
  return apiRequest<string[]>("/items/tags");
}

export async function createItem(input: CreateItemInput): Promise<Item> {
  return apiRequest<Item>("/items", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getItem(id: number): Promise<Item> {
  return apiRequest<Item>(`/items/${id}`);
}

export async function updateItem(id: number, input: UpdateItemInput): Promise<Item> {
  return apiRequest<Item>(`/items/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function deleteItem(id: number): Promise<void> {
  await apiRequest<void>(`/items/${id}`, {
    method: "DELETE",
  });
}
