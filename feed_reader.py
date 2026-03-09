import re
import html
import feedparser
from newspaper import Article

SUMMARY_MIN_LENGTH = 150


def load_sources(path="sources.txt") -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_full_content(url: str, char_limit: int = 1200) -> str:
    """Scrapes full article body from a URL. Returns empty string on failure."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return clean_text(article.text)[:char_limit]
    except Exception as e:
        print(f"Scraping failed for {url}: {e}")
        return ""


def fetch_articles(rss_url: str, limit: int = 10) -> list[dict]:
    feed = feedparser.parse(rss_url)
    articles = []
    source_name = feed.feed.get("title", "Unknown Source")

    for entry in feed.entries[:limit]:
        title = clean_text(entry.get("title", ""))
        summary = clean_text(entry.get("summary", entry.get("description", "")))
        link = entry.get("link", "").strip()

        if title and link:
            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary,
                "link": link,
                "published": entry.get("published_parsed"),  # struct_time or None
            })

    return articles