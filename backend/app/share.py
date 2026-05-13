from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse


URL_RE = re.compile(r"https?://[^\s<>'\"，。；;！!）)】》]+")
TRAILING_PUNCTUATION = ".,，。;；!！?？)]}】》\"'"


def extract_first_url(value: str) -> Optional[str]:
    match = URL_RE.search(value)
    if not match:
        return None
    return match.group(0).rstrip(TRAILING_PUNCTUATION)


def title_from_share_text(raw_text: str, url: str) -> Optional[str]:
    if raw_text.strip() == url:
        return None

    before_url = raw_text.split(url, 1)[0]
    candidates = [
        line.strip()
        for line in before_url.splitlines()
        if line.strip() and "复制" not in line and "查看详情" not in line
    ]
    if not candidates:
        return None

    title = " ".join(candidates[0].split())
    return title[:240] or None


def inferred_tags(url: str, raw_text: str) -> list[str]:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    path = parsed.path.lower()
    text = raw_text.lower()

    tags: list[str] = []
    if "xiaohongshu.com" in hostname or hostname == "xhslink.com":
        if "/collection/" in path:
            tags.append("collection")
        elif hostname == "xhslink.com" and path.startswith("/m/"):
            tags.append("profile")
        elif "/user/profile" in path or "主页" in raw_text:
            tags.append("profile")
        else:
            tags.append("post")
    elif "douyin.com" in hostname:
        if "/user/" in path or "主页" in raw_text or "profile" in text:
            tags.append("profile")
        elif "collection" in path or "favorite" in path:
            tags.append("collection")
        else:
            tags.append("post")

    return tags
