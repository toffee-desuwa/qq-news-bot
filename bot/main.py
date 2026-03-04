"""CLI entry point and top-level orchestration."""

import argparse
import io
import os
import sys


def _fix_stdout_encoding() -> None:
    """Ensure stdout/stderr can handle UTF-8 (needed on Windows with GBK)."""
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )


_fix_stdout_encoding()


def _load_dotenv(path: str = ".env") -> None:
    """Load key=value pairs from a .env file into os.environ (stdlib only).

    Skips blank lines and comments. Does not override existing env vars.
    """
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bot",
        description="QQ news bot -- OneBot v11 RSS digest bot.",
    )
    parser.add_argument(
        "--connect",
        action="store_true",
        help="Connect to OneBot WS and start the bot loop.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without connecting to OneBot.",
    )
    parser.add_argument(
        "--news",
        action="store_true",
        help="Fetch and print news to stdout (useful with --dry-run).",
    )
    parser.add_argument(
        "--alerts",
        metavar="KEYWORD",
        type=str,
        default=None,
        help="Simulate alert matching for KEYWORD (useful with --dry-run).",
    )
    return parser


def main() -> None:
    _load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    if not args.connect and not args.dry_run:
        parser.print_help()
        sys.exit(1)

    if args.dry_run and args.news:
        from bot.news_fetcher import fetch_all, format_news
        print("[dry-run] fetching news ...")
        items = fetch_all()
        print(format_news(items))
        return

    if args.dry_run and args.alerts:
        _run_dry_alerts(args.alerts)
        return

    if args.connect:
        _run_connect()
        return

    # dry-run without --news: just confirm startup
    print("[dry-run] bot started (no action requested)")


def _run_dry_alerts(keyword: str) -> None:
    """Simulate one alert poll cycle with a temporary subscription."""
    import tempfile
    from bot.alerts import process_alerts, keyword_match, format_alert, link_hash
    from bot.news_fetcher import fetch_all
    from bot.storage import Storage

    print(f"[dry-run] simulating alerts for keyword: {keyword}")
    print("[dry-run] fetching feeds ...")
    items = fetch_all(max_items=50)
    print(f"[dry-run] fetched {len(items)} items, matching against \"{keyword}\" ...\n")

    matched = 0
    for item in items:
        kw = keyword_match(item.title, [keyword.lower()])
        if kw is not None:
            print(format_alert(item, kw))
            print()
            matched += 1

    if matched == 0:
        print(f"[dry-run] no items matched keyword \"{keyword}\".")
    else:
        print(f"[dry-run] {matched} item(s) matched.")


def _run_connect() -> None:
    from bot.onebot_ws import OneBotWS
    from bot.commands import handle_command, get_storage
    from bot.news_fetcher import fetch_all, format_news
    from bot.scheduler import Scheduler
    from bot.alert_poller import AlertPoller

    def on_message(msg: dict) -> None:
        if msg.get("post_type") != "message":
            return
        if msg.get("message_type") != "group":
            return
        raw_text = msg.get("raw_message", "") or msg.get("message", "")
        group_id = msg.get("group_id", 0)
        if not raw_text or not group_id:
            return
        reply = handle_command(raw_text, group_id)
        if reply:
            ws.send_group_msg(group_id, reply)

    ws = OneBotWS(on_message=on_message)
    storage = get_storage()

    scheduler = Scheduler(
        send_fn=ws.send_group_msg,
        get_groups_fn=storage.list_subscribed,
        get_news_fn=lambda: format_news(fetch_all()),
    )
    scheduler.start()

    poller = AlertPoller(storage=storage, send_fn=ws.send_group_msg)
    poller.start()

    print(f"[connect] starting bot, target: {ws.url}")
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n[connect] shutting down")
        poller.stop()
        scheduler.stop()
        ws.stop()
