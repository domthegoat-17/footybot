from pathlib import Path
import feedparser
from openai import OpenAI
from discord_post import post_to_discord

client = OpenAI()


def load_sources(path="sources.txt"):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def get_seen_links(file_path="seen_links.txt"):
    path = Path(file_path)
    if not path.exists():
        return set()

    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def add_seen_link(link, file_path="seen_links.txt"):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def fetch_articles(rss_url, limit=5):
    feed = feedparser.parse(rss_url)
    articles = []

    source_name = feed.feed.get("title", "Unknown Source")

    for entry in feed.entries[:limit]:
        title = entry.get("title", "").strip()
        summary = entry.get("summary", entry.get("description", "")).strip()
        link = entry.get("link", "").strip()

        if title and link:
            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary,
                "link": link,
            })

    return articles


def generate_ai_script(article_title, summary):
    prompt = f"""
Write a 50-second YouTube Short script about this football story.

Title:
{article_title}

Details:
{summary}

Tone:
Hype football fan commentary with slang like:
'generational talent', 'bottled it', 'here we go' but dont make it TOO CORNY, NO EMOJIS. If the details are too short, focus the script on the historical rivalry or recent form of the teams involved.

Structure:
HOOK (dont include this word in the script)
THE TEA (dont include this word in the script)
HOT TAKE (dont include this word in the script)
QUESTION (dont include this word in the script)

Keep it under 120 words.
""".strip()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a football YouTube Shorts scriptwriter."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.strip()


def post_script(article, script):
    message = f""" **FOOTYBOT SCRIPT**

**Source:** {article['source']}
**Topic:** {article['title']}
**Link:** {article['link']}

```text
{script}
```"""

    post_to_discord(message)


if __name__ == "__main__":
    sources = load_sources("sourses.txt")
    seen_links = get_seen_links()

    all_articles = []

    for url in sources:
        articles = fetch_articles(url, limit=5)
        new_articles = [a for a in articles if a["link"] not in seen_links]
        all_articles.extend(new_articles)

    if not all_articles:
        print("No new stories found. Channel is safe from spam!")

    for article in all_articles[:3]:
        script = generate_ai_script(article["title"], article["summary"])
        post_script(article, script)
        add_seen_link(article["link"])
        print(f"Posted: {article['title']}")