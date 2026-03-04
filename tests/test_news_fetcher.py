"""Tests for bot.news_fetcher."""

import unittest

from bot.news_fetcher import NewsItem, parse_feed_xml, format_news, fetch_all
from bot.news_sources import display_name

RSS_SAMPLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>First Article</title>
      <link>https://example.com/1</link>
    </item>
    <item>
      <title>Second Article</title>
      <link>https://example.com/2</link>
    </item>
  </channel>
</rss>
"""

ATOM_SAMPLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <entry>
    <title>Atom Entry One</title>
    <link href="https://example.com/a1"/>
  </entry>
  <entry>
    <title>Atom Entry Two</title>
    <link href="https://example.com/a2"/>
  </entry>
</feed>
"""


class TestParseFeedXml(unittest.TestCase):
    def test_parse_rss(self):
        items = parse_feed_xml(RSS_SAMPLE, "TestSrc")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "First Article")
        self.assertEqual(items[0].source, "TestSrc")
        self.assertEqual(items[1].link, "https://example.com/2")

    def test_parse_atom(self):
        items = parse_feed_xml(ATOM_SAMPLE, "AtomSrc")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Atom Entry One")
        self.assertEqual(items[0].link, "https://example.com/a1")
        self.assertEqual(items[1].source, "AtomSrc")

    def test_parse_empty(self):
        xml = '<?xml version="1.0"?><rss><channel></channel></rss>'
        items = parse_feed_xml(xml, "Empty")
        self.assertEqual(items, [])


class TestFormatNews(unittest.TestCase):
    def test_chinese_header_and_items(self):
        items = [
            NewsItem("Title A", "https://a.com", "SrcA"),
            NewsItem("Title B", "https://b.com", "SrcB"),
        ]
        text = format_news(items)
        # Header must be Chinese with count, sources
        self.assertIn("\u4eca\u65e5\u5feb\u8baf", text)  # "今日快讯"
        self.assertIn("2\u6761", text)  # "2条"
        self.assertIn("SrcA", text)
        self.assertIn("SrcB", text)
        # Items must use Chinese brackets
        self.assertIn("\u3010SrcA\u3011Title A", text)  # "【SrcA】"
        self.assertIn("https://a.com", text)
        # Footer
        self.assertIn("\u6807\u9898\u4fdd\u7559\u539f\u6587", text)  # "标题保留原文"

    def test_format_empty(self):
        text = format_news([])
        self.assertIn("\u6682\u65e0\u65b0\u95fb", text)  # "暂无新闻"


class TestDisplayName(unittest.TestCase):
    def test_known_source_mapped(self):
        self.assertEqual(display_name("Hacker News"), "\u9ed1\u5ba2\u65b0\u95fb")
        self.assertEqual(display_name("ChinaDaily"), "\u4e2d\u56fd\u65e5\u62a5")
        self.assertEqual(display_name("IT Home"), "IT\u4e4b\u5bb6")

    def test_unknown_source_unchanged(self):
        self.assertEqual(display_name("UnknownFeed"), "UnknownFeed")

    def test_format_news_uses_chinese_source(self):
        items = [
            NewsItem("Some Title", "https://example.com/1", "Hacker News"),
        ]
        text = format_news(items)
        self.assertIn("\u3010\u9ed1\u5ba2\u65b0\u95fb\u3011", text)  # 【黑客新闻】
        self.assertNotIn("\u3010Hacker News\u3011", text)


class TestDedupe(unittest.TestCase):
    def test_dedupe_by_link(self):
        """Items with the same link from different sources should be deduped."""
        from unittest.mock import patch

        items_a = [NewsItem("Dup", "https://same.com/1", "FeedA")]
        items_b = [NewsItem("Dup Copy", "https://same.com/1", "FeedB")]
        items_c = [NewsItem("Unique", "https://unique.com/1", "FeedC")]

        mock_sources = [("FeedA", "http://a", 5), ("FeedB", "http://b", 5),
                        ("FeedC", "http://c", 5)]

        def fake_fetch(name, url, timeout=10):
            return {"FeedA": items_a, "FeedB": items_b, "FeedC": items_c}[name]

        with patch("bot.news_fetcher.DEFAULT_SOURCES", mock_sources), \
             patch("bot.news_fetcher.fetch_feed", side_effect=fake_fetch):
            result = fetch_all(max_items=10)

        links = [item.link for item in result]
        self.assertEqual(links.count("https://same.com/1"), 1)
        self.assertIn("https://unique.com/1", links)

    def test_per_source_cap(self):
        """Per-source cap should limit items from a single feed."""
        from unittest.mock import patch

        many_items = [NewsItem(f"T{i}", f"https://a.com/{i}", "BigFeed")
                      for i in range(10)]
        mock_sources = [("BigFeed", "http://big", 3)]

        with patch("bot.news_fetcher.DEFAULT_SOURCES", mock_sources), \
             patch("bot.news_fetcher.fetch_feed", return_value=many_items):
            result = fetch_all(max_items=10)

        self.assertEqual(len(result), 3)

    def test_feed_failure_skipped(self):
        """A failing feed should not break the whole digest."""
        from unittest.mock import patch

        good_items = [NewsItem("Good", "https://good.com/1", "GoodFeed")]
        mock_sources = [("BadFeed", "http://bad", 5),
                        ("GoodFeed", "http://good", 5)]

        def fake_fetch(name, url, timeout=10):
            if name == "BadFeed":
                return []  # simulates fetch failure (fail-open returns [])
            return good_items

        with patch("bot.news_fetcher.DEFAULT_SOURCES", mock_sources), \
             patch("bot.news_fetcher.fetch_feed", side_effect=fake_fetch):
            result = fetch_all(max_items=10)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Good")


if __name__ == "__main__":
    unittest.main()
