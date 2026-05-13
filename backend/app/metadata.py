from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT_SECONDS = 7
USER_AGENT = "RecallBox/1.0 (+https://localhost; metadata preview)"


@dataclass
class MetadataResult:
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error: Optional[str] = None


def _content(soup: BeautifulSoup, *, property_name: Optional[str] = None, name: Optional[str] = None) -> Optional[str]:
    attrs: dict[str, str] = {}
    if property_name:
        attrs["property"] = property_name
    if name:
        attrs["name"] = name

    tag = soup.find("meta", attrs=attrs)
    value = tag.get("content") if tag else None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def extract_metadata(url: str) -> MetadataResult:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return MetadataResult(error=str(exc))

    content_type = response.headers.get("content-type", "")
    if content_type and "html" not in content_type.lower():
        return MetadataResult(error=f"Unsupported content type: {content_type}")

    soup = BeautifulSoup(response.text, "html.parser")
    title = _content(soup, property_name="og:title")
    description = _content(soup, property_name="og:description") or _content(soup, name="description")
    thumbnail_url = _content(soup, property_name="og:image")

    if not title and soup.title and soup.title.string:
        title = soup.title.string

    title = _text(title)
    description = _text(description)
    thumbnail_url = urljoin(response.url, thumbnail_url) if thumbnail_url else None

    return MetadataResult(title=title, description=description, thumbnail_url=thumbnail_url)
