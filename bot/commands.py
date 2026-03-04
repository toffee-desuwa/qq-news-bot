"""Command router for group messages."""

from typing import Optional

from bot.news_fetcher import fetch_all, format_news
from bot.rate_limit import RateLimiter

# Shared rate limiter for /news (60s cooldown per group)
_news_limiter = RateLimiter(cooldown_seconds=60)

HELP_TEXT = (
    "qq-news-bot commands:\n"
    "/help -- show this message\n"
    "/news -- latest news from RSS sources\n"
    "/subscribe -- enable daily digest for this group\n"
    "/unsubscribe -- disable daily digest for this group"
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
        return f"Rate limited. Try again in {secs}s."
    items = fetch_all()
    return format_news(items)


def _handle_subscribe(group_id: int) -> str:
    # Placeholder -- storage wiring in Commit 5
    return "subscribe: not yet implemented"


def _handle_unsubscribe(group_id: int) -> str:
    # Placeholder -- storage wiring in Commit 5
    return "unsubscribe: not yet implemented"
