# qq-news-bot

A QQ group chat bot that aggregates news from RSS feeds and pushes daily
digests. Built on the OneBot v11 protocol (tested with NapCat) over
WebSocket.

## Status

v0.1.0 -- MVP, local-first, stdlib-only.

## Features

- `/help` -- list available commands.
- `/news` -- fetch and display latest news items from configured RSS sources.
- `/subscribe` -- enable daily digest push for the current group.
- `/unsubscribe` -- disable daily digest for the current group.
- Scheduled daily digest at a configurable time.
- Per-group rate limiting on `/news`.

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
# Edit .env -- set ONEBOT_WS_URL to your NapCat WS endpoint
python -m bot --connect
```

The bot connects via WebSocket, listens for group messages, and responds
to `/help`, `/news`, `/subscribe`, and `/unsubscribe`. A background
scheduler pushes daily digests to subscribed groups at the configured time.

### 4. CLI reference

```
python -m bot --help          # show usage
python -m bot --dry-run       # start without OneBot (no-op)
python -m bot --dry-run --news  # fetch + print news
python -m bot --connect       # connect to OneBot and run
```

## Configuration

Copy `.env.example` to `.env` and edit:

| Variable              | Default           | Description                     |
|-----------------------|-------------------|---------------------------------|
| ONEBOT_WS_URL         | (required)        | WS endpoint for NapCat          |
| ONEBOT_ACCESS_TOKEN   | (empty)           | Optional auth token             |
| DAILY_TIME            | 20:00             | Daily digest time (HH:MM)      |
| TIMEZONE              | Asia/Shanghai     | Scheduler timezone              |
| NEWS_MAX_ITEMS        | 8                 | Max items per digest            |
| STORAGE_PATH          | ./data/bot.sqlite | SQLite database path            |

## Limitations

- RSS only. No API-based news sources in v0.1.
- No LLM integration -- items are presented as-is (title + source + link).
- No realtime breaking-news alerts; digest is scheduled, not event-driven.
- Tested with NapCat only; other OneBot v11 implementations may work but
  are not verified.
- No web UI or admin panel. All config is via environment variables.
- Rate limiting is in-memory and resets on restart.

## License

MIT
