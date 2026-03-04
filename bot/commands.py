"""Command router for group messages."""

import time
from typing import Optional

from bot.news_fetcher import fetch_all, format_news
from bot.rate_limit import RateLimiter
from bot.skills_loader import get_text
from bot.storage import Storage

# Shared rate limiter for /news (60s cooldown per group)
_news_limiter = RateLimiter(cooldown_seconds=60)

# Module-level storage instance, initialized lazily
_storage: Optional[Storage] = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage


def set_storage(storage: Storage) -> None:
    """Inject a storage instance (useful for testing)."""
    global _storage
    _storage = storage


def _build_help() -> str:
    lines = [
        get_text("help_header"),
        get_text("help_news"),
        get_text("help_subscribe"),
        get_text("help_unsubscribe"),
        get_text("help_sub"),
        get_text("help_unsub"),
        get_text("help_subs"),
        get_text("help_mute"),
        get_text("help_unmute"),
    ]
    return "\n".join(lines)


def handle_command(raw_text: str, group_id: int) -> Optional[str]:
    """Route a command string and return a reply, or None if not a command."""
    text = raw_text.strip()
    if not text.startswith("/"):
        return None

    parts = text.split()
    cmd = parts[0].lower()
    arg = " ".join(parts[1:]).strip() if len(parts) > 1 else ""

    if cmd == "/help":
        return _build_help()

    if cmd == "/news":
        return _handle_news(group_id)

    if cmd == "/subscribe":
        return _handle_subscribe(group_id)

    if cmd == "/unsubscribe":
        return _handle_unsubscribe(group_id)

    if cmd == "/sub":
        return _handle_sub(group_id, arg)

    if cmd == "/unsub":
        return _handle_unsub(group_id, arg)

    if cmd == "/subs":
        return _handle_subs(group_id)

    if cmd == "/mute":
        return _handle_mute(group_id, arg)

    if cmd == "/unmute":
        return _handle_unmute(group_id)

    return None


def _handle_news(group_id: int) -> str:
    key = f"news:{group_id}"
    if not _news_limiter.check(key):
        secs = _news_limiter.remaining(key)
        return get_text("news_cooldown", secs=secs)
    items = fetch_all()
    return format_news(items)


def _handle_subscribe(group_id: int) -> str:
    store = get_storage()
    if store.subscribe(group_id):
        return get_text("subscribe_ok")
    return get_text("subscribe_dup")


def _handle_unsubscribe(group_id: int) -> str:
    store = get_storage()
    if store.unsubscribe(group_id):
        return get_text("unsubscribe_ok")
    return get_text("unsubscribe_none")


def _handle_sub(group_id: int, keyword: str) -> str:
    if not keyword:
        return get_text("sub_usage")
    store = get_storage()
    if store.add_keyword(group_id, keyword):
        return get_text("sub_ok", keyword=keyword.lower())
    return get_text("sub_dup", keyword=keyword.lower())


def _handle_unsub(group_id: int, keyword: str) -> str:
    if not keyword:
        return get_text("unsub_usage")
    store = get_storage()
    if store.remove_keyword(group_id, keyword):
        return get_text("unsub_ok", keyword=keyword.lower())
    return get_text("unsub_none", keyword=keyword.lower())


def _handle_subs(group_id: int) -> str:
    store = get_storage()
    keywords = store.list_keywords(group_id)
    if not keywords:
        return get_text("subs_empty")
    kw_list = "\u3001".join(keywords)
    return get_text("subs_list", count=len(keywords), keywords=kw_list)


def _handle_mute(group_id: int, arg: str) -> str:
    if not arg:
        return get_text("mute_usage")
    try:
        minutes = int(arg)
    except ValueError:
        return get_text("mute_bad_arg")
    if minutes <= 0:
        return get_text("mute_negative")
    if minutes > 1440:
        minutes = 1440  # cap at 24 hours
    store = get_storage()
    until_ts = time.time() + minutes * 60
    store.set_mute(group_id, until_ts)
    return get_text("mute_ok", minutes=minutes)


def _handle_unmute(group_id: int) -> str:
    store = get_storage()
    if store.is_muted(group_id):
        store.clear_mute(group_id)
        return get_text("unmute_ok")
    return get_text("unmute_none")
