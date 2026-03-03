# Agent Brief -- qq-news-bot

This file encodes the project workflow, constraints, and validation steps
so they do not need to be repeated across conversations.

## Project

QQ group chat bot that fetches news from RSS feeds and pushes daily digests.
Built on OneBot v11 protocol via NapCat, using a WebSocket client.

## Tech constraints

- Python 3.10+ stdlib only. No third-party packages.
- SQLite for local storage.
- Config via environment variables (no config files beyond `.env.example`).
- All repo text in English. No emojis.

## Branch strategy

- Default branch: `main`
- Working branch: `release/v0.1.0`
- Do not merge, tag, or release without explicit approval.

## Commit workflow

After each commit:

1. Show `git diff --stat`.
2. Run validations (see below) and show short pass/fail summary.
3. Continue to next commit unless a hard gate applies.

Hard gates (must stop and wait for human review):

- After Commit 1 (scaffold).
- After all commits done + final validations pass (before push).

## Validations (run after every commit)

```bash
python -m compileall .
python -m unittest -q
python -m bot --dry-run --news
```

From Commit 4 onward, also run:

```bash
python -m bot --connect
# Should not crash immediately; will wait for WS -- verify startup then Ctrl-C.
```

## Commit plan

1. Scaffold: project structure, README skeleton, AGENT_BRIEF, STYLE_LOCK,
   .env.example, .gitignore, minimal CLI (`--dry-run --news` placeholder).
2. RSS fetch/parse/format (stdlib: urllib + xml.etree) + tests.
3. SQLite storage for subscriptions + tests.
4. OneBot WS client + send_group_msg + command router (/help, /news).
5. Scheduler + /subscribe + /unsubscribe + rate limit + README quickstart.

## Repo structure

```
bot/
  __init__.py
  __main__.py
  main.py
  onebot_ws.py
  commands.py
  news_sources.py
  news_fetcher.py
  storage.py
  scheduler.py
  rate_limit.py
tests/
  __init__.py
  test_commands.py
  test_storage.py
  test_news_fetcher.py
README.md
AGENT_BRIEF.md
STYLE_LOCK.md
.env.example
.gitignore
```

## Environment variables

| Variable              | Default              | Description                        |
|-----------------------|----------------------|------------------------------------|
| ONEBOT_WS_URL         | (required)           | WebSocket endpoint for NapCat      |
| ONEBOT_ACCESS_TOKEN   | (empty)              | Optional auth token                |
| DAILY_TIME            | 20:00                | Daily digest push time (HH:MM)    |
| TIMEZONE              | Asia/Shanghai        | Timezone for scheduler             |
| NEWS_MAX_ITEMS        | 8                    | Max items per digest               |
| STORAGE_PATH          | ./data/bot.sqlite    | SQLite database path               |
