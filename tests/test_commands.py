"""Tests for bot.commands."""

import os
import tempfile
import time
import unittest

from bot.commands import handle_command, set_storage
from bot.rate_limit import RateLimiter
from bot.storage import Storage


class TestHandleCommand(unittest.TestCase):
    def test_help(self):
        reply = handle_command("/help", group_id=1)
        self.assertIsNotNone(reply)
        self.assertIn("/news", reply)

    def test_not_a_command(self):
        reply = handle_command("hello world", group_id=1)
        self.assertIsNone(reply)

    def test_unknown_command(self):
        reply = handle_command("/unknown", group_id=1)
        self.assertIsNone(reply)

    def test_help_with_whitespace(self):
        reply = handle_command("  /help  ", group_id=1)
        self.assertIsNotNone(reply)
        self.assertIn("/news", reply)

    def test_help_lists_new_commands(self):
        reply = handle_command("/help", group_id=1)
        self.assertIn("/sub", reply)
        self.assertIn("/unsub", reply)
        self.assertIn("/subs", reply)
        self.assertIn("/mute", reply)
        self.assertIn("/unmute", reply)


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
        self.assertIn("\u5df2\u8ba2\u9605", reply)  # "已订阅"
        self.assertTrue(self._storage.is_subscribed(5000))

    def test_subscribe_duplicate(self):
        handle_command("/subscribe", group_id=5000)
        reply = handle_command("/subscribe", group_id=5000)
        self.assertIn("\u5df2\u7ecf\u8ba2\u9605", reply)  # "已经订阅"

    def test_unsubscribe(self):
        handle_command("/subscribe", group_id=6000)
        reply = handle_command("/unsubscribe", group_id=6000)
        self.assertIn("\u53d6\u6d88\u8ba2\u9605", reply)  # "取消订阅"
        self.assertFalse(self._storage.is_subscribed(6000))

    def test_unsubscribe_not_subscribed(self):
        reply = handle_command("/unsubscribe", group_id=7000)
        self.assertIn("\u672a\u8ba2\u9605", reply)  # "未订阅"


class TestAlertCommands(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self._storage = Storage(db_path=self._tmp.name)
        set_storage(self._storage)

    def tearDown(self):
        self._storage.close()
        os.unlink(self._tmp.name)
        set_storage(None)

    def test_sub_keyword(self):
        reply = handle_command("/sub AI", group_id=100)
        self.assertIn("ai", reply)
        self.assertIn("已订阅关键词", reply)
        self.assertIn("ai", self._storage.list_keywords(100))

    def test_sub_no_keyword(self):
        reply = handle_command("/sub", group_id=100)
        self.assertIn("用法", reply)

    def test_sub_duplicate(self):
        handle_command("/sub gpu", group_id=100)
        reply = handle_command("/sub GPU", group_id=100)
        self.assertIn("已订阅过", reply)

    def test_unsub_keyword(self):
        handle_command("/sub tesla", group_id=100)
        reply = handle_command("/unsub Tesla", group_id=100)
        self.assertIn("已取消关键词", reply)
        self.assertEqual(self._storage.list_keywords(100), [])

    def test_unsub_no_keyword(self):
        reply = handle_command("/unsub", group_id=100)
        self.assertIn("用法", reply)

    def test_unsub_absent(self):
        reply = handle_command("/unsub nope", group_id=100)
        self.assertIn("未找到", reply)

    def test_subs_empty(self):
        reply = handle_command("/subs", group_id=100)
        self.assertIn("暂无", reply)

    def test_subs_with_keywords(self):
        handle_command("/sub ai", group_id=100)
        handle_command("/sub gpu", group_id=100)
        reply = handle_command("/subs", group_id=100)
        self.assertIn("ai", reply)
        self.assertIn("gpu", reply)
        self.assertIn("2个", reply)

    def test_mute(self):
        reply = handle_command("/mute 30", group_id=100)
        self.assertIn("静音", reply)
        self.assertIn("30", reply)
        self.assertTrue(self._storage.is_muted(100))

    def test_mute_no_arg(self):
        reply = handle_command("/mute", group_id=100)
        self.assertIn("用法", reply)

    def test_mute_bad_arg(self):
        reply = handle_command("/mute abc", group_id=100)
        self.assertIn("整数", reply)

    def test_mute_negative(self):
        reply = handle_command("/mute -5", group_id=100)
        self.assertIn("正整数", reply)

    def test_mute_cap_at_1440(self):
        reply = handle_command("/mute 9999", group_id=100)
        self.assertIn("静音", reply)
        remaining = self._storage.mute_remaining(100)
        self.assertLessEqual(remaining, 1440)

    def test_unmute(self):
        handle_command("/mute 30", group_id=100)
        reply = handle_command("/unmute", group_id=100)
        self.assertIn("恢复", reply)
        self.assertFalse(self._storage.is_muted(100))

    def test_unmute_not_muted(self):
        reply = handle_command("/unmute", group_id=100)
        self.assertIn("未处于静音", reply)


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
