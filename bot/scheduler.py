"""Daily digest scheduler.

Runs in a background thread. At DAILY_TIME each day (in TIMEZONE),
fetches news and sends a digest to all subscribed groups.
"""

import os
import threading
import time
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Callable, Optional

from bot.skills_loader import get_text


def _parse_offset(tz_name: str) -> Optional[tzinfo]:
    """Convert a timezone name to a fixed UTC offset.

    Supports 'Asia/Shanghai' (UTC+8) and explicit UTC+N / UTC-N.
    Extend the mapping as needed.
    """
    known = {
        "Asia/Shanghai": 8,
        "Asia/Tokyo": 9,
        "Asia/Kolkata": 5.5,
        "Europe/London": 0,
        "America/New_York": -5,
        "America/Los_Angeles": -8,
        "UTC": 0,
    }
    if tz_name in known:
        hours = known[tz_name]
        return timezone(timedelta(hours=hours))
    # Try UTC+N / UTC-N format
    if tz_name.startswith("UTC"):
        try:
            offset = float(tz_name[3:])
            return timezone(timedelta(hours=offset))
        except (ValueError, IndexError):
            pass
    return timezone(timedelta(hours=8))  # fallback to CST


class Scheduler:
    """Simple daily digest scheduler running in a daemon thread."""

    def __init__(
        self,
        send_fn: Callable[[int, str], None],
        get_groups_fn: Callable[[], list],
        get_news_fn: Callable[[], str],
    ):
        self._send = send_fn
        self._get_groups = get_groups_fn
        self._get_news = get_news_fn
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        time_str = os.environ.get("DAILY_TIME", "20:00")
        parts = time_str.split(":")
        self._hour = int(parts[0])
        self._minute = int(parts[1]) if len(parts) > 1 else 0

        tz_name = os.environ.get("TIMEZONE", "Asia/Shanghai")
        self._tz = _parse_offset(tz_name)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[scheduler] started, daily digest at {self._hour:02d}:{self._minute:02d}")

    def stop(self) -> None:
        self._stop_event.set()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now(self._tz)
            target = now.replace(
                hour=self._hour, minute=self._minute, second=0, microsecond=0
            )
            if target <= now:
                target += timedelta(days=1)
            wait_secs = (target - now).total_seconds()
            # Sleep in short intervals so we can respond to stop quickly
            while wait_secs > 0 and not self._stop_event.is_set():
                time.sleep(min(wait_secs, 30))
                wait_secs -= 30

            if self._stop_event.is_set():
                break

            self._push_digest()

    def _push_digest(self) -> None:
        groups = self._get_groups()
        if not groups:
            print("[scheduler] no subscribed groups, skipping digest")
            return
        news_text = self._get_news()
        for gid in groups:
            try:
                prefix = get_text("digest_prefix")
                self._send(gid, f"{prefix}\n{news_text}")
            except Exception as exc:
                print(f"[scheduler] failed to send to {gid}: {exc}")
        print(f"[scheduler] digest sent to {len(groups)} group(s)")
