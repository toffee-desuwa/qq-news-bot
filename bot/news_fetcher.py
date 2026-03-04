"""RSS feed fetcher and formatter (stdlib only: urllib + xml.etree)."""

import os
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List

from bot.news_sources import DEFAULT_SOURCES

# Atom namespace
_ATOM_NS = "http://www.w3.org/2005/Atom"


@dataclass
class NewsItem:
    title: str
    link: str
    source: str


def parse_feed_xml(xml_text: str, source_name: str) -> List[NewsItem]:
    """Parse RSS 2.0 or Atom XML into NewsItem list."""
    root = ET.fromstring(xml_text)
    items: List[NewsItem] = []

    # RSS 2.0: <rss><channel><item>
    for item in root.iter("item"):
        title = _text(item, "title")
        link = _text(item, "link")
        if title and link:
            items.append(NewsItem(title=title.strip(), link=link.strip(),
                                  source=source_name))

    if items:
        return items

    # Atom: <feed><entry>
    for entry in root.iter(f"{{{_ATOM_NS}}}entry"):
        title = _text(entry, f"{{{_ATOM_NS}}}title")
        link_el = entry.find(f"{{{_ATOM_NS}}}link")
        link = link_el.get("href", "") if link_el is not None else ""
        if title and link:
            items.append(NewsItem(title=title.strip(), link=link.strip(),
                                  source=source_name))

    return items


def fetch_feed(name: str, url: str, timeout: int = 10) -> List[NewsItem]:
    """Fetch a single RSS/Atom feed and return parsed items."""
    req = urllib.request.Request(url, headers={"User-Agent": "qq-news-bot/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            xml_text = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        print(f"[warn] failed to fetch {name}: {exc}")
        return []
    return parse_feed_xml(xml_text, name)


def fetch_all(max_items: int = 0) -> List[NewsItem]:
    """Fetch all configured sources. Return up to max_items total."""
    if max_items <= 0:
        max_items = int(os.environ.get("NEWS_MAX_ITEMS", "8"))
    all_items: List[NewsItem] = []
    for name, url in DEFAULT_SOURCES:
        all_items.extend(fetch_feed(name, url))
        if len(all_items) >= max_items:
            break
    return all_items[:max_items]


def format_news(items: List[NewsItem]) -> str:
    """Format news items into a readable message string."""
    if not items:
        return "No news fetched. Sources may be unreachable."
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. [{item.source}] {item.title}\n   {item.link}")
    return "\n".join(lines)


def _text(parent: ET.Element, tag: str) -> str:
    """Get text content of a child element, or empty string."""
    el = parent.find(tag)
    return el.text if el is not None and el.text else ""
