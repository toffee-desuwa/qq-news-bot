# qq-news-bot

A QQ group chat bot that aggregates news from RSS feeds and pushes daily
digests. Built on the OneBot v11 protocol (tested with NapCat) over
WebSocket. Stdlib-only, no third-party dependencies.

## Status

v0.1.1 -- local-first, stdlib-only, Chinese output.

## Features

- `/help` -- list available commands (Chinese).
- `/news` -- fetch and display latest news from RSS sources.
- `/subscribe` -- enable daily digest push for the current group.
- `/unsubscribe` -- disable daily digest for the current group.
- Scheduled daily digest at a configurable time.
- Per-group rate limiting on `/news` (60s cooldown).

## Requirements

- Python 3.10+
- A running OneBot v11 implementation (e.g. NapCat) with WebSocket enabled.

## Quickstart

### 1. Test the news pipeline (no OneBot needed)

```bash
python -m bot --dry-run --news
```

This fetches live RSS feeds and prints formatted news to stdout.

### 2. Run tests

```bash
python -m unittest -q
```

### 3. Connect to OneBot

Make sure NapCat (or another OneBot v11 implementation) is running with
WebSocket enabled.

```bash
cp .env.example .env
# Edit .env: set ONEBOT_WS_URL and ONEBOT_ACCESS_TOKEN
python -m bot --connect
```

The bot connects via WebSocket, listens for group messages, and responds
to commands. A background scheduler pushes daily digests to subscribed
groups at the configured time.

### 4. Test commands in a QQ group

Send `/help` in any group where the bot account is a member. Then try
`/news` to fetch a live digest, and `/subscribe` to enable daily push.

### 5. CLI reference

```
python -m bot --help            # show usage
python -m bot --dry-run         # start without OneBot (no-op)
python -m bot --dry-run --news  # fetch + print news
python -m bot --connect         # connect to OneBot and run
```

## Example `/news` output

```
📰 今日快讯（8条）｜更新：20:00（Asia/Shanghai）｜来源：36Kr、Hacker News、Solidot

1.【Hacker News】Show HN: Open-source local-first sync engine
   🔗 https://example.com/1
2.【Solidot】Linux 6.14 内核发布
   🔗 https://www.solidot.org/story?sid=12345
3.【36Kr】何小鹏：自动驾驶将在未来1-3年真正到来
   🔗 https://36kr.com/p/1234567

提示：标题保留原文；点链接看全文。
```

Titles stay in their original language; the shell (header, tags, footer) is
Chinese.

## RSS sources

Default feeds (v0.1.1): Hacker News, Solidot, ChinaDaily, 36Kr, IT Home,
Zhihu Daily, Reuters, BBC News, The Verge, Ars Technica.

Source strategy:

- Per-source cap (2-3 items each) prevents any single feed from dominating.
- Items are merged and deduped by link before truncating to NEWS_MAX_ITEMS.
- Fail-open: if a feed is unreachable or returns bad XML, it is skipped with
  a one-line log. The rest of the digest still works.

## Configuration

Copy `.env.example` to `.env` and edit:

| Variable              | Default           | Description                     |
|-----------------------|-------------------|---------------------------------|
| ONEBOT_WS_URL         | (required)        | WS endpoint for NapCat          |
| ONEBOT_ACCESS_TOKEN   | (empty)           | Auth token (must match NapCat)  |
| DAILY_TIME            | 20:00             | Daily digest time (HH:MM)      |
| TIMEZONE              | Asia/Shanghai     | Scheduler timezone              |
| NEWS_MAX_ITEMS        | 8                 | Max items per digest            |
| STORAGE_PATH          | ./data/bot.sqlite | SQLite database path            |

## Limitations

- RSS only. No API-based news sources.
- No LLM integration -- items are presented as-is (title + source + link).
- No realtime breaking-news alerts; digest is scheduled, not event-driven.
- Tested with NapCat only; other OneBot v11 implementations may work but
  are not verified.
- No web UI or admin panel. All config is via environment variables.
- Rate limiting is in-memory and resets on restart.
- Some feeds may be blocked by network conditions (proxies, firewalls).

## License

MIT
