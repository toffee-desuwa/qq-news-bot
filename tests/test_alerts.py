"""Tests for bot.alerts."""

import os
import tempfile
import time
import unittest

from bot.alerts import (
    keyword_match,
    link_hash,
    format_alert,
    format_overflow,
    process_alerts,
)
from bot.news_fetcher import NewsItem
from bot.storage import Storage


class TestKeywordMatch(unittest.TestCase):
    def test_match_exact(self):
        self.assertEqual(keyword_match("AI revolution", ["ai"]), "ai")

    def test_match_case_insensitive(self):
        self.assertEqual(keyword_match("New GPU released", ["gpu"]), "gpu")

    def test_match_first_keyword_wins(self):
        result = keyword_match("AI GPU chip", ["gpu", "ai"])
        self.assertEqual(result, "gpu")

    def test_no_match(self):
        self.assertIsNone(keyword_match("Weather update", ["ai", "gpu"]))

    def test_match_substring(self):
        self.assertEqual(keyword_match("Tesla stock rises", ["tesla"]), "tesla")

    def test_empty_keywords(self):
        self.assertIsNone(keyword_match("Anything", []))


class TestLinkHash(unittest.TestCase):
    def test_deterministic(self):
        h1 = link_hash("https://example.com/1")
        h2 = link_hash("https://example.com/1")
        self.assertEqual(h1, h2)

    def test_different_links_differ(self):
        h1 = link_hash("https://example.com/1")
        h2 = link_hash("https://example.com/2")
        self.assertNotEqual(h1, h2)


class TestFormatAlert(unittest.TestCase):
    def test_format_contains_all_parts(self):
        item = NewsItem("Breaking News Title", "https://example.com/1", "Reuters")
        text = format_alert(item, "breaking")
        self.assertIn("突发快讯", text)
        self.assertIn("【Reuters】", text)
        self.assertIn("Breaking News Title", text)
        self.assertIn("https://example.com/1", text)
        self.assertIn("breaking", text)


class TestFormatOverflow(unittest.TestCase):
    def test_overflow_message(self):
        text = format_overflow(3)
        self.assertIn("3", text)
        self.assertIn("省略", text)


class TestProcessAlerts(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self.storage = Storage(db_path=self._tmp.name)

    def tearDown(self):
        self.storage.close()
        os.unlink(self._tmp.name)

    def _make_items(self, titles_and_links):
        return [NewsItem(t, l, "TestSrc") for t, l in titles_and_links]

    def test_basic_match(self):
        self.storage.add_keyword(100, "ai")
        items = self._make_items([("AI breakthrough", "https://a.com/1")])
        result = process_alerts(self.storage, items=items)
        self.assertIn(100, result)
        self.assertEqual(len(result[100]), 1)
        self.assertIn("AI breakthrough", result[100][0])

    def test_no_match(self):
        self.storage.add_keyword(100, "quantum")
        items = self._make_items([("AI news", "https://a.com/1")])
        result = process_alerts(self.storage, items=items)
        self.assertEqual(result, {})

    def test_dedupe_skips_seen(self):
        self.storage.add_keyword(100, "ai")
        lh = link_hash("https://a.com/1")
        self.storage.mark_seen(100, lh)
        items = self._make_items([("AI news", "https://a.com/1")])
        result = process_alerts(self.storage, items=items)
        self.assertEqual(result, {})

    def test_rate_limit_caps_alerts(self):
        os.environ["ALERT_MAX_PER_GROUP"] = "2"
        try:
            self.storage.add_keyword(100, "ai")
            items = self._make_items([
                ("AI one", "https://a.com/1"),
                ("AI two", "https://a.com/2"),
                ("AI three", "https://a.com/3"),
                ("AI four", "https://a.com/4"),
            ])
            result = process_alerts(self.storage, items=items)
            messages = result[100]
            # 2 full alerts + 1 overflow summary
            self.assertEqual(len(messages), 3)
            self.assertIn("2", messages[-1])  # "2 条" overflow
        finally:
            os.environ.pop("ALERT_MAX_PER_GROUP", None)

    def test_muted_group_skipped(self):
        self.storage.add_keyword(100, "ai")
        self.storage.set_mute(100, time.time() + 600)
        items = self._make_items([("AI news", "https://a.com/1")])
        result = process_alerts(self.storage, items=items)
        self.assertEqual(result, {})

    def test_mute_expired_not_skipped(self):
        self.storage.add_keyword(100, "ai")
        self.storage.set_mute(100, time.time() - 1)
        items = self._make_items([("AI news", "https://a.com/1")])
        result = process_alerts(self.storage, items=items)
        self.assertIn(100, result)

    def test_multiple_groups(self):
        self.storage.add_keyword(100, "ai")
        self.storage.add_keyword(200, "gpu")
        items = self._make_items([
            ("AI chip", "https://a.com/1"),
            ("New GPU", "https://a.com/2"),
        ])
        result = process_alerts(self.storage, items=items)
        self.assertIn(100, result)
        self.assertIn(200, result)

    def test_empty_items(self):
        self.storage.add_keyword(100, "ai")
        result = process_alerts(self.storage, items=[])
        self.assertEqual(result, {})

    def test_no_groups_with_keywords(self):
        items = self._make_items([("AI news", "https://a.com/1")])
        result = process_alerts(self.storage, items=items)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
