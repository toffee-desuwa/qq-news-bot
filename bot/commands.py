"""Command router for group messages."""

import time
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
    "/unsubscribe \u2014 关闭每日推送\n"
    "/sub <关键词> \u2014 订阅突发快讯关键词\n"
    "/unsub <关键词> \u2014 取消关键词订阅\n"
    "/subs \u2014 查看本群已订阅关键词\n"
    "/mute <分钟> \u2014 暂停快讯推送\n"
    "/unmute \u2014 恢复快讯推送"
)


def handle_command(raw_text: str, group_id: int) -> Optional[str]:
    """Route a command string and return a reply, or None if not a command."""
    text = raw_text.strip()
    if not text.startswith("/"):
        return None

    parts = text.split()
    cmd = parts[0].lower()
    arg = " ".join(parts[1:]).strip() if len(parts) > 1 else ""

    if cmd == "/help":
        return HELP_TEXT

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


def _handle_sub(group_id: int, keyword: str) -> str:
    if not keyword:
        return "\u26a0\ufe0f 用法：/sub <关键词>"
    store = get_storage()
    if store.add_keyword(group_id, keyword):
        return f"\u2705 已订阅关键词「{keyword.lower()}」，匹配时将推送快讯。"
    return f"\u2139\ufe0f 关键词「{keyword.lower()}」已订阅过了。"


def _handle_unsub(group_id: int, keyword: str) -> str:
    if not keyword:
        return "\u26a0\ufe0f 用法：/unsub <关键词>"
    store = get_storage()
    if store.remove_keyword(group_id, keyword):
        return f"\U0001f6d1 已取消关键词「{keyword.lower()}」。"
    return f"\u2139\ufe0f 未找到关键词「{keyword.lower()}」。"


def _handle_subs(group_id: int) -> str:
    store = get_storage()
    keywords = store.list_keywords(group_id)
    if not keywords:
        return "\U0001f4ed 本群暂无订阅关键词。使用 /sub <关键词> 添加。"
    kw_list = "、".join(keywords)
    return f"\U0001f514 本群订阅关键词（{len(keywords)}个）：{kw_list}"


def _handle_mute(group_id: int, arg: str) -> str:
    if not arg:
        return "\u26a0\ufe0f 用法：/mute <分钟数>"
    try:
        minutes = int(arg)
    except ValueError:
        return "\u26a0\ufe0f 请输入整数分钟数，例如 /mute 30"
    if minutes <= 0:
        return "\u26a0\ufe0f 分钟数需为正整数。"
    if minutes > 1440:
        minutes = 1440  # cap at 24 hours
    store = get_storage()
    until_ts = time.time() + minutes * 60
    store.set_mute(group_id, until_ts)
    return f"\U0001f507 快讯已静音 {minutes} 分钟。使用 /unmute 可提前恢复。"


def _handle_unmute(group_id: int) -> str:
    store = get_storage()
    if store.is_muted(group_id):
        store.clear_mute(group_id)
        return "\U0001f50a 快讯已恢复推送。"
    return "\u2139\ufe0f 本群未处于静音状态。"
