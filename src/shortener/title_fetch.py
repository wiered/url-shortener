from __future__ import annotations

import html
import re

import httpx

_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE | re.DOTALL)


def _extract_title(html_text: str) -> str | None:
    m = _TITLE_RE.search(html_text)
    if not m:
        return None
    raw = m.group(1)
    raw = re.sub(r"\s+", " ", raw.replace("\n", " ")).strip()
    if not raw:
        return None
    return html.unescape(raw)


def fetch_page_title(url: str, timeout: float = 5.0) -> str | None:
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; URL-Shortener/0.1; +https://example.invalid)"
                ),
            },
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "").lower()
            if "json" in ct and "html" not in ct:
                return None
            return _extract_title(resp.text)
    except Exception:
        return None
