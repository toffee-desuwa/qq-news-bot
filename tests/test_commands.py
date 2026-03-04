"""Tests for bot.commands."""

import unittest

from bot.commands import handle_command, HELP_TEXT
from bot.rate_limit import RateLimiter


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
