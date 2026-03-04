"""Tests for bot.news_fetcher."""

import unittest

from bot.news_fetcher import NewsItem, parse_feed_xml, format_news

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
    def test_format_items(self):
        items = [
            NewsItem("Title A", "https://a.com", "SrcA"),
            NewsItem("Title B", "https://b.com", "SrcB"),
        ]
        text = format_news(items)
        self.assertIn("1. [SrcA] Title A", text)
        self.assertIn("2. [SrcB] Title B", text)
        self.assertIn("https://b.com", text)

    def test_format_empty(self):
        text = format_news([])
        self.assertIn("No news fetched", text)


if __name__ == "__main__":
    unittest.main()
