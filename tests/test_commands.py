"""Tests for bot.commands."""

import os
import tempfile
import unittest

from bot.commands import handle_command, HELP_TEXT, set_storage
from bot.rate_limit import RateLimiter
from bot.storage import Storage


class TestHandleCommand(unittest.TestCase):
    def test_help(self):
        reply = handle_command("/help", group_id=1)
        self.assertEqual(reply, HELP_TEXT)

    def test_not_a_command(self):
        reply = handle_command("hello world", group_id=1)
        self.assertIsNone(reply)

    def test_unknown_command(self):
        reply = handle_command("/unknown", group_id=1)
        self.assertIsNone(reply)

    def test_help_with_whitespace(self):
        reply = handle_command("  /help  ", group_id=1)
        self.assertEqual(reply, HELP_TEXT)


class TestSubscribeCommands(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self._storage = Storage(db_path=self._tmp.name)
        set_storage(self._storage)

    def tearDown(self):
        self._storage.close()
        os.unlink(self._tmp.name)
        set_storage(None)

    def test_subscribe(self):
        reply = handle_command("/subscribe", group_id=5000)
        self.assertIn("Subscribed", reply)
        self.assertTrue(self._storage.is_subscribed(5000))

    def test_subscribe_duplicate(self):
        handle_command("/subscribe", group_id=5000)
        reply = handle_command("/subscribe", group_id=5000)
        self.assertIn("already subscribed", reply)

    def test_unsubscribe(self):
        handle_command("/subscribe", group_id=6000)
        reply = handle_command("/unsubscribe", group_id=6000)
        self.assertIn("Unsubscribed", reply)
        self.assertFalse(self._storage.is_subscribed(6000))

    def test_unsubscribe_not_subscribed(self):
        reply = handle_command("/unsubscribe", group_id=7000)
        self.assertIn("not subscribed", reply)


class TestRateLimiter(unittest.TestCase):
    def test_first_call_allowed(self):
        rl = RateLimiter(cooldown_seconds=60)
        self.assertTrue(rl.check("key1"))

    def test_second_call_blocked(self):
        rl = RateLimiter(cooldown_seconds=60)
        rl.check("key2")
        self.assertFalse(rl.check("key2"))

    def test_different_keys_independent(self):
        rl = RateLimiter(cooldown_seconds=60)
        self.assertTrue(rl.check("a"))
        self.assertTrue(rl.check("b"))

    def test_remaining_after_check(self):
        rl = RateLimiter(cooldown_seconds=60)
        rl.check("r")
        self.assertGreater(rl.remaining("r"), 0)

    def test_remaining_no_check(self):
        rl = RateLimiter(cooldown_seconds=60)
        self.assertEqual(rl.remaining("never"), 0)


if __name__ == "__main__":
    unittest.main()
