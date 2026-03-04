"""Alert poller: runs in a daemon thread, polls feeds every 15 minutes.

For each poll cycle, fetches feeds once, then dispatches keyword-matched
alerts to subscribed groups via the alert engine.
"""

import threading
import time
from typing import Callable

from bot.alerts import process_alerts
from bot.storage import Storage

POLL_INTERVAL = 15 * 60  # 15 minutes


class AlertPoller:
    """Daemon thread that polls feeds and dispatches alerts."""

    def __init__(
        self,
        storage: Storage,
        send_fn: Callable[[int, str], None],
    ):
        self._storage = storage
        self._send = send_fn
        self._thread = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[alert-poller] started, polling every {POLL_INTERVAL // 60} min")

    def stop(self) -> None:
        self._stop_event.set()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._poll_once()
            # Prune old seen records weekly-ish (every cycle is fine, it's fast)
            self._storage.prune_seen()
            # Sleep in short intervals for responsive shutdown
            remaining = POLL_INTERVAL
            while remaining > 0 and not self._stop_event.is_set():
                time.sleep(min(remaining, 30))
                remaining -= 30

    def _poll_once(self) -> None:
        try:
            alerts = process_alerts(self._storage)
        except Exception as exc:
            print(f"[alert-poller] poll error: {exc}")
            return

        total = 0
        for gid, messages in alerts.items():
            for msg in messages:
                try:
                    self._send(gid, msg)
                    total += 1
                except Exception as exc:
                    print(f"[alert-poller] send error (group {gid}): {exc}")

        if total > 0:
            print(f"[alert-poller] dispatched {total} alert(s) to {len(alerts)} group(s)")
