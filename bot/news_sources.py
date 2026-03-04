"""RSS feed source definitions.

Each source is (display_name, url, per_source_cap).
per_source_cap limits how many items we take from each feed before merging.
"""

# 8-12 stable feeds covering tech, general news, and Chinese sources.
# Per-source cap keeps any single feed from dominating the digest.
DEFAULT_SOURCES = [
    ("Hacker News",   "https://hnrss.org/newest?count=10",                          3),
    ("Solidot",       "https://www.solidot.org/index.rss",                           2),
    ("ChinaDaily",    "https://www.chinadaily.com.cn/rss/china_rss.xml",             2),
    ("36Kr",          "https://36kr.com/feed",                                       2),
    ("IT Home",       "https://www.ithome.com/rss/",                                 2),
    ("Zhihu Daily",   "https://rss.mifaw.com/articles/5c8bb11a3c41f61efd36683e/5c91d2e23c41f61efd3c69a7", 2),
    ("Reuters",       "https://feeds.reuters.com/reuters/topNews",                   2),
    ("BBC News",      "https://feeds.bbci.co.uk/news/rss.xml",                       2),
    ("The Verge",     "https://www.theverge.com/rss/index.xml",                      2),
    ("Ars Technica",  "https://feeds.arstechnica.com/arstechnica/index",             2),
]

# Chinese-friendly display names for the output shell.
# Used only at render time; NewsItem.source stays as-is for logic/storage.
_DISPLAY_NAMES = {
    "Hacker News":  "黑客新闻",
    "ChinaDaily":   "中国日报",
    "IT Home":      "IT之家",
    "Zhihu Daily":  "知乎日报",
    "Reuters":      "路透社",
    "BBC News":     "BBC新闻",
    "The Verge":    "The Verge",
    "Ars Technica": "Ars Technica",
    "Solidot":      "Solidot",
    "36Kr":         "36氪",
}


def display_name(source: str) -> str:
    """Return a Chinese-friendly display label for a source key.

    Unknown sources are returned unchanged.
    """
    return _DISPLAY_NAMES.get(source, source)
