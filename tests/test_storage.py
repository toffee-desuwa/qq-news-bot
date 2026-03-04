"""Tests for bot.storage."""

import os
import tempfile
import time
import unittest
from unittest.mock import patch

from bot.storage import Storage


class TestStorage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self.storage = Storage(db_path=self._tmp.name)

    def tearDown(self):
        self.storage.close()
        os.unlink(self._tmp.name)

    def test_subscribe_new_group(self):
        self.assertTrue(self.storage.subscribe(12345))
        self.assertTrue(self.storage.is_subscribed(12345))

    def test_subscribe_duplicate(self):
        self.storage.subscribe(12345)
        self.assertFalse(self.storage.subscribe(12345))

    def test_unsubscribe(self):
        self.storage.subscribe(99999)
        self.assertTrue(self.storage.unsubscribe(99999))
        self.assertFalse(self.storage.is_subscribed(99999))

    def test_unsubscribe_nonexistent(self):
        self.assertFalse(self.storage.unsubscribe(77777))

    def test_list_subscribed(self):
        self.storage.subscribe(100)
        self.storage.subscribe(200)
        self.storage.subscribe(300)
        result = self.storage.list_subscribed()
        self.assertEqual(sorted(result), [100, 200, 300])

    def test_list_empty(self):
        self.assertEqual(self.storage.list_subscribed(), [])


class TestAlertKeywords(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self.storage = Storage(db_path=self._tmp.name)

    def tearDown(self):
        self.storage.close()
        os.unlink(self._tmp.name)

    def test_add_keyword(self):
        self.assertTrue(self.storage.add_keyword(100, "AI"))
        self.assertIn("ai", self.storage.list_keywords(100))

    def test_add_keyword_duplicate(self):
        self.storage.add_keyword(100, "AI")
        self.assertFalse(self.storage.add_keyword(100, "ai"))

    def test_add_keyword_normalizes_case(self):
        self.storage.add_keyword(100, "  Tesla  ")
        self.assertIn("tesla", self.storage.list_keywords(100))

    def test_remove_keyword(self):
        self.storage.add_keyword(100, "gpu")
        self.assertTrue(self.storage.remove_keyword(100, "GPU"))
        self.assertEqual(self.storage.list_keywords(100), [])

    def test_remove_keyword_absent(self):
        self.assertFalse(self.storage.remove_keyword(100, "nope"))

    def test_list_keywords_sorted(self):
        self.storage.add_keyword(100, "zebra")
        self.storage.add_keyword(100, "alpha")
        self.storage.add_keyword(100, "mid")
        self.assertEqual(self.storage.list_keywords(100), ["alpha", "mid", "zebra"])

    def test_list_keywords_empty(self):
        self.assertEqual(self.storage.list_keywords(999), [])

    def test_groups_with_keywords(self):
        self.storage.add_keyword(100, "ai")
        self.storage.add_keyword(200, "gpu")
        groups = self.storage.groups_with_keywords()
        self.assertEqual(sorted(groups), [100, 200])

    def test_groups_with_keywords_empty(self):
        self.assertEqual(self.storage.groups_with_keywords(), [])

    def test_keywords_isolated_per_group(self):
        self.storage.add_keyword(100, "ai")
        self.storage.add_keyword(200, "gpu")
        self.assertEqual(self.storage.list_keywords(100), ["ai"])
        self.assertEqual(self.storage.list_keywords(200), ["gpu"])


class TestMuteState(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self.storage = Storage(db_path=self._tmp.name)

    def tearDown(self):
        self.storage.close()
        os.unlink(self._tmp.name)

    def test_not_muted_by_default(self):
        self.assertFalse(self.storage.is_muted(100))

    def test_mute_active(self):
        self.storage.set_mute(100, time.time() + 600)
        self.assertTrue(self.storage.is_muted(100))

    def test_mute_expired(self):
        self.storage.set_mute(100, time.time() - 1)
        self.assertFalse(self.storage.is_muted(100))

    def test_clear_mute(self):
        self.storage.set_mute(100, time.time() + 600)
        self.storage.clear_mute(100)
        self.assertFalse(self.storage.is_muted(100))

    def test_mute_remaining_active(self):
        self.storage.set_mute(100, time.time() + 300)
        remaining = self.storage.mute_remaining(100)
        self.assertGreater(remaining, 0)
        self.assertLessEqual(remaining, 5)

    def test_mute_remaining_not_muted(self):
        self.assertEqual(self.storage.mute_remaining(100), 0)

    def test_mute_remaining_expired(self):
        self.storage.set_mute(100, time.time() - 10)
        self.assertEqual(self.storage.mute_remaining(100), 0)


class TestSeenAlerts(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self.storage = Storage(db_path=self._tmp.name)

    def tearDown(self):
        self.storage.close()
        os.unlink(self._tmp.name)

    def test_mark_and_check_seen(self):
        self.storage.mark_seen(100, "abc123")
        self.assertTrue(self.storage.is_seen(100, "abc123"))

    def test_not_seen_by_default(self):
        self.assertFalse(self.storage.is_seen(100, "xyz"))

    def test_seen_isolated_per_group(self):
        self.storage.mark_seen(100, "hash1")
        self.assertFalse(self.storage.is_seen(200, "hash1"))

    def test_mark_seen_idempotent(self):
        self.storage.mark_seen(100, "dup")
        self.storage.mark_seen(100, "dup")
        self.assertTrue(self.storage.is_seen(100, "dup"))

    def test_prune_seen(self):
        # Insert an old record by manipulating ts directly
        self.storage._conn.execute(
            "INSERT INTO seen_alerts (group_id, link_hash, ts) VALUES (?, ?, ?)",
            (100, "old", time.time() - 86400 * 30),
        )
        self.storage.mark_seen(100, "new")
        deleted = self.storage.prune_seen(max_age_seconds=86400 * 7)
        self.assertEqual(deleted, 1)
        self.assertFalse(self.storage.is_seen(100, "old"))
        self.assertTrue(self.storage.is_seen(100, "new"))


if __name__ == "__main__":
    unittest.main()
