# qq-news-bot

A QQ group chat bot that aggregates news from RSS feeds, pushes daily
digests, and delivers keyword-based breaking-news alerts. Built on
OneBot v11 (tested with NapCat) over WebSocket. Stdlib-only, no
third-party dependencies.

## Status

v0.2.0 -- keyword alerts, per-group mute, skills-based persona.

## Features

### Digest commands

- `/help` -- list available commands (Chinese).
- `/news` -- fetch and display latest news from RSS sources.
- `/subscribe` -- enable daily digest push for the current group.
- `/unsubscribe` -- disable daily digest for the current group.

### Alert commands (new in v0.2.0)

- `/sub <keyword>` -- subscribe to breaking-news alerts for a keyword.
- `/unsub <keyword>` -- unsubscribe a keyword.
- `/subs` -- list current alert keywords for this group.
- `/mute <minutes>` -- mute alerts for this group (max 24 h).
- `/unmute` -- resume alerts.

### Polling model

Feeds are polled every **15 minutes** (not realtime). When a new item
matches a subscribed keyword, the bot sends an alert to that group only.
Alerts are deduplicated per group (by link hash) and rate-limited to
`ALERT_MAX_PER_GROUP` per cycle (default 2). Overflow is summarized.

### Persona (optional skill pack)

Persona is an optional template layer that changes the bot's wording
(help text, command replies, alert phrasing). Default is `neutral`
(concise, tool-like). Set `PERSONA=maid_cat` in `.env` for a playful
alternative. Persona never affects core logic.

## Requirements

- Python 3.10+
- A running OneBot v11 implementation (e.g. NapCat) with WebSocket enabled.

## Quickstart

### 1. Test the news pipeline (no OneBot needed)

```bash
python -m bot --dry-run --news
```

This fetches live RSS feeds and prints formatted news to stdout.

### 2. Test alert matching

```bash
python -m bot --dry-run --alerts "AI"
```

Fetches feeds and shows which items match the keyword.

### 3. Run tests

```bash
python -m unittest -q
```

### 4. Connect to OneBot

Make sure NapCat (or another OneBot v11 implementation) is running with
WebSocket enabled.

```bash
cp .env.example .env
# Edit .env: set ONEBOT_WS_URL and ONEBOT_ACCESS_TOKEN
python -m bot --connect
```

The bot connects via WebSocket, listens for group messages, and responds
to commands. A background scheduler pushes daily digests. A separate
alert poller checks feeds every 15 minutes for keyword matches.

### 5. CLI reference

```
python -m bot --help                # show usage
python -m bot --dry-run             # start without OneBot (no-op)
python -m bot --dry-run --news      # fetch + print news
python -m bot --dry-run --alerts K  # simulate alert matching for keyword K
python -m bot --connect             # connect to OneBot and run
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

## Example alert output

```
🚨 突发快讯
【Hacker News】OpenAI releases new reasoning model
🔗 https://news.ycombinator.com/item?id=12345
🔍 匹配关键词：ai

🚨 突发快讯
【36Kr】百度发布文心大模型 4.5
🔗 https://36kr.com/p/9876543
🔍 匹配关键词：ai

... 还有 1 条相关快讯被省略（频率限制）。
```

Titles stay in their original language; the shell (header, tags, footer)
is Chinese.

## RSS sources

Default feeds (v0.2.0): Hacker News, Solidot, ChinaDaily, 36Kr, IT Home,
Zhihu Daily, Reuters, BBC News, The Verge, Ars Technica.

Source strategy:

- Per-source cap (2-3 items each) prevents any single feed from dominating.
- Items are merged and deduped by link before truncating to NEWS_MAX_ITEMS.
- Fail-open: if a feed is unreachable or returns bad XML, it is skipped with
  a one-line log. The rest of the digest still works.

## Configuration

Copy `.env.example` to `.env` and edit:

| Variable              | Default           | Description                        |
|-----------------------|-------------------|------------------------------------|
| ONEBOT_WS_URL         | (required)        | WS endpoint for NapCat             |
| ONEBOT_ACCESS_TOKEN   | (empty)           | Auth token (must match NapCat)     |
| DAILY_TIME            | 20:00             | Daily digest time (HH:MM)         |
| TIMEZONE              | Asia/Shanghai     | Scheduler timezone                 |
| NEWS_MAX_ITEMS        | 8                 | Max items per digest               |
| STORAGE_PATH          | ./data/bot.sqlite | SQLite database path               |
| ALERT_MAX_PER_GROUP   | 2                 | Max alerts per group per poll      |
| PERSONA               | neutral           | Persona skill pack (neutral/maid_cat) |

## Limitations

- RSS only. No API-based news sources.
- No LLM integration -- items are presented as-is (title + source + link).
- Alerts are keyword-based (substring match). They may miss events phrased
  differently or fire on unrelated articles containing the keyword.
- Polling interval is fixed at 15 minutes; this is not true realtime push.
- Per-group rate limits cap alerts per cycle. Use `/mute` if it's still noisy.
- Tested with NapCat only; other OneBot v11 implementations may work but
  are not verified.
- No web UI or admin panel. All config is via environment variables.
- Rate limiting is in-memory and resets on restart; mute/keywords/seen state
  is persisted in SQLite.
- Some feeds may be blocked by network conditions (proxies, firewalls).
- Platform risk: QQ/NapCat may change APIs or policies without notice.

## License

MIT
