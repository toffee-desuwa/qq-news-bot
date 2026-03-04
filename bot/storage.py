"""SQLite storage for group subscriptions."""

import os
import sqlite3
from pathlib import Path
from typing import List


def _default_db_path() -> str:
    return os.environ.get("STORAGE_PATH", "./data/bot.sqlite")


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


class Storage:
    """Manages subscription state in a local SQLite database."""

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or _default_db_path()
        _ensure_parent(self.db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._init_tables()

    def _init_tables(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS subscriptions ("
            "  group_id INTEGER PRIMARY KEY"
            ")"
        )
        self._conn.commit()

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

    def close(self) -> None:
        self._conn.close()
