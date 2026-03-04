"""Alert engine: keyword matching, per-group dedupe, and rate-limited alert dispatch."""

import hashlib
import os
from typing import Dict, List, Optional, Tuple

from bot.news_fetcher import NewsItem, fetch_all
from bot.news_sources import display_name
from bot.skills_loader import get_text
from bot.storage import Storage


def keyword_match(title: str, keywords: List[str]) -> Optional[str]:
    """Return the first keyword that matches the title (case-insensitive), or None."""
    title_lower = title.lower()
    for kw in keywords:
        if kw in title_lower:
            return kw
    return None


def link_hash(link: str) -> str:
    """Stable short hash for deduplication."""
    return hashlib.md5(link.encode()).hexdigest()[:12]


def format_alert(item: NewsItem, matched_keyword: str) -> str:
    """Format a single alert message (Chinese shell + original title)."""
    header = get_text("alert_header")
    kw_line = get_text("alert_keyword", keyword=matched_keyword)
    return (
        f"{header}\n"
        f"\u3010{display_name(item.source)}\u3011{item.title}\n"
        f"\U0001f517 {item.link}\n"
        f"{kw_line}"
    )


def format_overflow(count: int) -> str:
    """Format the 'and N more' summary when rate limit is hit."""
    return get_text("alert_overflow", count=count)


def process_alerts(
    storage: Storage,
    items: Optional[List[NewsItem]] = None,
) -> Dict[int, List[str]]:
    """Run one alert poll cycle.

    Returns {group_id: [formatted_message, ...]} for groups that have
    unseen, non-muted, keyword-matched alerts (rate-limited).
    """
    max_per_group = int(os.environ.get("ALERT_MAX_PER_GROUP", "2"))

    if items is None:
        items = fetch_all(max_items=50)

    groups = storage.groups_with_keywords()
    if not groups or not items:
        return {}

    result: Dict[int, List[str]] = {}

    for gid in groups:
        if storage.is_muted(gid):
            continue

        keywords = storage.list_keywords(gid)
        if not keywords:
            continue

        matched: List[Tuple[NewsItem, str]] = []
        for item in items:
            lh = link_hash(item.link)
            if storage.is_seen(gid, lh):
                continue
            kw = keyword_match(item.title, keywords)
            if kw is not None:
                matched.append((item, kw))
                storage.mark_seen(gid, lh)

        if not matched:
            continue

        messages: List[str] = []
        sent = 0
        overflow = 0
        for item, kw in matched:
            if sent < max_per_group:
                messages.append(format_alert(item, kw))
                sent += 1
            else:
                overflow += 1

        if overflow > 0:
            messages.append(format_overflow(overflow))

        result[gid] = messages

    return result
