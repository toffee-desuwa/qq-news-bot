"""Command router for group messages."""

from typing import Optional

from bot.news_fetcher import fetch_all, format_news
from bot.rate_limit import RateLimiter
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

HELP_TEXT = (
    "\U0001f916 qq-news-bot 指令：\n"
    "/help \u2014 显示本帮助\n"
    "/news \u2014 获取最新新闻\n"
    "/subscribe \u2014 开启每日推送\n"
    "/unsubscribe \u2014 关闭每日推送"
)


def handle_command(raw_text: str, group_id: int) -> Optional[str]:
    """Route a command string and return a reply, or None if not a command."""
    text = raw_text.strip()
    if not text.startswith("/"):
        return None

    cmd = text.split()[0].lower()

    if cmd == "/help":
        return HELP_TEXT

    if cmd == "/news":
        return _handle_news(group_id)

    if cmd == "/subscribe":
        return _handle_subscribe(group_id)

    if cmd == "/unsubscribe":
        return _handle_unsubscribe(group_id)

    return None


def _handle_news(group_id: int) -> str:
    key = f"news:{group_id}"
    if not _news_limiter.check(key):
        secs = _news_limiter.remaining(key)
        return f"\u23f3 冷却中，{secs}秒后再试。"
    items = fetch_all()
    return format_news(items)


def _handle_subscribe(group_id: int) -> str:
    store = get_storage()
    if store.subscribe(group_id):
        return "\u2705 已订阅，本群将收到每日新闻推送。"
    return "\u2139\ufe0f 本群已经订阅过了。"


def _handle_unsubscribe(group_id: int) -> str:
    store = get_storage()
    if store.unsubscribe(group_id):
        return "\U0001f6d1 已取消订阅，不再推送每日新闻。"
    return "\u2139\ufe0f 本群未订阅。"
