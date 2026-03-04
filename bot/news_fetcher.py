"""RSS feed fetcher and formatter (stdlib only: urllib + xml.etree).

v0.1.1: per-source cap, dedupe by link, fail-open, Chinese output shell.
"""

import os
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    """Fetch a single RSS/Atom feed and return parsed items.

    Fail-open: returns empty list on error, logs one line.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "qq-news-bot/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            xml_text = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        print(f"[warn] feed skip: {name} ({exc})")
        return []
    try:
        return parse_feed_xml(xml_text, name)
    except ET.ParseError as exc:
        print(f"[warn] feed parse error: {name} ({exc})")
        return []


def fetch_all(max_items: int = 0) -> List[NewsItem]:
    """Fetch all configured sources with per-source cap, dedupe, and limit.

    Strategy: take up to `cap` items per feed, merge, dedupe by link,
    then truncate to max_items.
    """
    if max_items <= 0:
        max_items = int(os.environ.get("NEWS_MAX_ITEMS", "8"))

    all_items: List[NewsItem] = []
    seen_links: set = set()

    for name, url, cap in DEFAULT_SOURCES:
        feed_items = fetch_feed(name, url)
        added = 0
        for item in feed_items:
            if item.link in seen_links:
                continue
            seen_links.add(item.link)
            all_items.append(item)
            added += 1
            if added >= cap:
                break

    return all_items[:max_items]


def format_news(items: List[NewsItem]) -> str:
    """Format news items into a Chinese-shell message.

    Header: Chinese with count, timestamp, timezone, sources.
    Items: numbered with source tag and link.
    Footer: reminder that titles are in original language.
    """
    if not items:
        return "暂无新闻，RSS 源可能不可用。"

    tz_name = os.environ.get("TIMEZONE", "Asia/Shanghai")
    tz_offset = _tz_offset(tz_name)
    now = datetime.now(tz_offset)
    time_str = now.strftime("%H:%M")

    sources = sorted(set(item.source for item in items))
    source_str = "、".join(sources)

    lines = []
    lines.append(
        f"\U0001f4f0 今日快讯（{len(items)}条）"
        f"\uff5c更新：{time_str}（{tz_name}）"
        f"\uff5c来源：{source_str}"
    )
    lines.append("")

    for i, item in enumerate(items, 1):
        lines.append(f"{i}.\u3010{item.source}\u3011{item.title}")
        lines.append(f"   \U0001f517 {item.link}")

    lines.append("")
    lines.append("提示：标题保留原文；点链接看全文。")

    return "\n".join(lines)


def _text(parent: ET.Element, tag: str) -> str:
    """Get text content of a child element, or empty string."""
    el = parent.find(tag)
    return el.text if el is not None and el.text else ""


def _tz_offset(tz_name: str) -> timezone:
    """Convert timezone name to fixed UTC offset. Fallback: UTC+8."""
    known = {
        "Asia/Shanghai": 8, "Asia/Tokyo": 9, "Asia/Kolkata": 5.5,
        "Europe/London": 0, "America/New_York": -5, "America/Los_Angeles": -8,
        "UTC": 0,
    }
    hours = known.get(tz_name)
    if hours is not None:
        return timezone(timedelta(hours=hours))
    if tz_name.startswith("UTC"):
        try:
            return timezone(timedelta(hours=float(tz_name[3:])))
        except (ValueError, IndexError):
            pass
    return timezone(timedelta(hours=8))
