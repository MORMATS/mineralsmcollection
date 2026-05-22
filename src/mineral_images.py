from __future__ import annotations

import html
import re
from typing import Any

import requests


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_HEADERS = {"User-Agent": "mineral-collection-app/1.0"}
BAD_TITLE_WORDS = {
    "diagram",
    "formula",
    "icon",
    "logo",
    "map",
    "structure",
    "symbol",
}


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()


def commons_page_url(title: str) -> str:
    return f"https://commons.wikimedia.org/wiki/{title.replace(' ', '_')}"


def metadata_text(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key, {})
    if isinstance(value, dict):
        return clean_html(str(value.get("value") or ""))
    return clean_html(str(value or ""))


def image_from_page(page: dict[str, Any]) -> dict[str, str] | None:
    title = str(page.get("title") or "")
    lower_title = title.lower()
    if not title or any(word in lower_title for word in BAD_TITLE_WORDS):
        return None

    image_infos = page.get("imageinfo") or []
    if not image_infos:
        return None

    info = image_infos[0]
    thumbnail_url = info.get("thumburl") or info.get("url")
    image_url = info.get("url") or thumbnail_url
    if not thumbnail_url or not image_url:
        return None

    metadata = info.get("extmetadata") or {}
    artist = metadata_text(metadata, "Artist")
    license_name = metadata_text(metadata, "LicenseShortName")
    credit = metadata_text(metadata, "Credit")
    object_name = metadata_text(metadata, "ObjectName") or title.replace("File:", "")

    caption_parts = [object_name]
    attribution = ", ".join(part for part in [artist, license_name] if part)
    if attribution:
        caption_parts.append(attribution)

    return {
        "title": title,
        "thumbnail_url": thumbnail_url,
        "image_url": image_url,
        "page_url": commons_page_url(title),
        "caption": " - ".join(caption_parts),
        "credit": credit,
    }


def find_commons_mineral_image(name: str) -> dict[str, str] | None:
    """Return a generic Wikimedia Commons mineral photo, when one is available."""
    queries = [
        f"{name} mineral specimen",
        f"{name} crystal",
        name,
    ]

    for query in queries:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrlimit": "8",
            "gsrsearch": query,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": "900",
        }

        try:
            resp = requests.get(
                COMMONS_API,
                params=params,
                headers=COMMONS_HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            continue

        pages = (payload.get("query") or {}).get("pages") or {}
        for page in pages.values():
            image = image_from_page(page)
            if image:
                return image
    return None
