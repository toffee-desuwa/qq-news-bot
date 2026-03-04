"""SQLite storage for group subscriptions, alert keywords, mute state, and seen alerts."""

import os
import sqlite3
import time
from pathlib import Path
from typing import List


def _default_db_path() -> str:
    return os.environ.get("STORAGE_PATH", "./data/bot.sqlite")


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


class Storage:
    """Manages subscription and alert state in a local SQLite database."""

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or _default_db_path()
        _ensure_parent(self.db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._init_tables()

    def _init_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                group_id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS alert_keywords (
                group_id INTEGER NOT NULL,
                keyword  TEXT NOT NULL,
                PRIMARY KEY (group_id, keyword)
            );
            CREATE TABLE IF NOT EXISTS mute_state (
                group_id INTEGER PRIMARY KEY,
                until_ts REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS seen_alerts (
                group_id  INTEGER NOT NULL,
                link_hash TEXT NOT NULL,
                ts        REAL NOT NULL,
                PRIMARY KEY (group_id, link_hash)
            );
        """)
        self._conn.commit()

    # ── daily digest subscriptions ──

    def subscribe(self, group_id: int) -> bool:
        """Subscribe a group. Returns True if newly subscribed, False if already."""
        try:
            self._conn.execute(
                "INSERT INTO subscriptions (group_id) VALUES (?)", (group_id,)
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def unsubscribe(self, group_id: int) -> bool:
        """Unsubscribe a group. Returns True if was subscribed, False otherwise."""
        cur = self._conn.execute(
            "DELETE FROM subscriptions WHERE group_id = ?", (group_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    def is_subscribed(self, group_id: int) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM subscriptions WHERE group_id = ?", (group_id,)
        )
        return cur.fetchone() is not None

    def list_subscribed(self) -> List[int]:
        """Return all subscribed group IDs."""
        cur = self._conn.execute("SELECT group_id FROM subscriptions")
        return [row[0] for row in cur.fetchall()]

    # ── alert keyword subscriptions ──

    def add_keyword(self, group_id: int, keyword: str) -> bool:
        """Add an alert keyword for a group. Returns True if newly added."""
        keyword = keyword.strip().lower()
        try:
            self._conn.execute(
                "INSERT INTO alert_keywords (group_id, keyword) VALUES (?, ?)",
                (group_id, keyword),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_keyword(self, group_id: int, keyword: str) -> bool:
        """Remove an alert keyword. Returns True if was present."""
        keyword = keyword.strip().lower()
        cur = self._conn.execute(
            "DELETE FROM alert_keywords WHERE group_id = ? AND keyword = ?",
            (group_id, keyword),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def list_keywords(self, group_id: int) -> List[str]:
        """Return all alert keywords for a group."""
        cur = self._conn.execute(
            "SELECT keyword FROM alert_keywords WHERE group_id = ? ORDER BY keyword",
            (group_id,),
        )
        return [row[0] for row in cur.fetchall()]

    def groups_with_keywords(self) -> List[int]:
        """Return group IDs that have at least one alert keyword."""
        cur = self._conn.execute(
            "SELECT DISTINCT group_id FROM alert_keywords"
        )
        return [row[0] for row in cur.fetchall()]

    # ── mute state ──

    def set_mute(self, group_id: int, until_ts: float) -> None:
        """Mute alerts for a group until the given Unix timestamp."""
        self._conn.execute(
            "INSERT OR REPLACE INTO mute_state (group_id, until_ts) VALUES (?, ?)",
            (group_id, until_ts),
        )
        self._conn.commit()

    def clear_mute(self, group_id: int) -> None:
        self._conn.execute(
            "DELETE FROM mute_state WHERE group_id = ?", (group_id,)
        )
        self._conn.commit()

    def is_muted(self, group_id: int) -> bool:
        """Return True if the group is currently muted."""
        cur = self._conn.execute(
            "SELECT until_ts FROM mute_state WHERE group_id = ?", (group_id,)
        )
        row = cur.fetchone()
        if row is None:
            return False
        if time.time() >= row[0]:
            # Mute expired — clean up
            self.clear_mute(group_id)
            return False
        return True

    def mute_remaining(self, group_id: int) -> int:
        """Minutes remaining on mute, or 0 if not muted."""
        cur = self._conn.execute(
            "SELECT until_ts FROM mute_state WHERE group_id = ?", (group_id,)
        )
        row = cur.fetchone()
        if row is None:
            return 0
        left = row[0] - time.time()
        if left <= 0:
            self.clear_mute(group_id)
            return 0
        return max(1, int(left / 60))

    # ── seen alerts (per-group dedupe) ──

    def mark_seen(self, group_id: int, link_hash: str) -> None:
        """Record that a group has seen this alert."""
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_alerts (group_id, link_hash, ts) "
            "VALUES (?, ?, ?)",
            (group_id, link_hash, time.time()),
        )
        self._conn.commit()

    def is_seen(self, group_id: int, link_hash: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM seen_alerts WHERE group_id = ? AND link_hash = ?",
            (group_id, link_hash),
        )
        return cur.fetchone() is not None

    def prune_seen(self, max_age_seconds: int = 86400 * 7) -> int:
        """Delete seen_alerts older than max_age_seconds. Returns count deleted."""
        cutoff = time.time() - max_age_seconds
        cur = self._conn.execute(
            "DELETE FROM seen_alerts WHERE ts < ?", (cutoff,)
        )
        self._conn.commit()
        return cur.rowcount

    def close(self) -> None:
        self._conn.close()
