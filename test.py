from pathlib import Path
import re
import html
import feedparser
from openai import OpenAI
from discord_post import post_to_discord

client = OpenAI()


def load_sources(path="sourses.txt"):
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


def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_articles(rss_url, limit=10):
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
            })

    return articles


def is_soccer_story(title, summary):
    text = (title + " " + summary).lower()

    nfl_terms = [
        "nfl", "touchdown", "touchdowns", "quarterback", "super bowl",
        "interception", "gridiron", "wide receiver", "linebacker"
    ]
    if any(term in text for term in nfl_terms):
        return False

    soccer_terms = [
        "football", "soccer", "premier league", "champions league",
        "europa league", "conference league", "club world cup",
        "transfer", "la liga", "serie a", "bundesliga", "ligue 1",
        "fifa", "uefa", "goal", "hat-trick", "relegation",
        "ballon d'or", "manager", "striker", "midfielder", "defender",
        "goalkeeper", "penalty", "red card", "clean sheet", "fixture"
    ]

    clubs_and_nations = [
        "arsenal", "chelsea", "liverpool", "manchester united",
        "manchester city", "tottenham", "spurs", "newcastle",
        "aston villa", "barcelona", "barca", "real madrid",
        "atletico madrid", "bayern", "dortmund", "juventus",
        "inter milan", "ac milan", "napoli", "psg",
        "england", "france", "spain", "portugal", "brazil",
        "argentina", "germany", "italy", "netherlands"
    ]

    return any(term in text for term in soccer_terms) or any(team in text for team in clubs_and_nations)


def get_heat_score(title, summary):
    text = (title + " " + summary).lower()
    score = 0

    weights = {
        # Huge engagement
        "here we go": 40,
        "breaking": 25,
        "exclusive": 22,
        "official": 20,
        "confirmed": 18,

        # Transfer / manager chaos
        "transfer": 18,
        "bid": 12,
        "medical": 16,
        "deal": 12,
        "signing": 14,
        "loan": 10,
        "release clause": 16,
        "sacked": 24,
        "manager": 8,
        "appointed": 14,

        # Drama / controversy
        "controversy": 18,
        "drama": 14,
        "row": 12,
        "clash": 12,
        "fuming": 14,
        "slammed": 12,
        "angry": 10,
        "ban": 16,
        "suspension": 16,

        # Match chaos / moments
        "injury": 18,
        "injured": 18,
        "red card": 16,
        "penalty": 10,
        "comeback": 16,
        "stoppage time": 12,
        "last-minute": 14,
        "winner": 10,
        "equaliser": 8,
        "hat-trick": 14,
        "record": 12,
        "historic": 16,

        # Stakes
        "title race": 18,
        "relegation": 16,
        "knockout": 14,
        "semi-final": 14,
        "final": 18,
        "derby": 18,

        # Injuries before big moments
        "doubt": 10,
        "ruled out": 16,
        "miss": 8,
    }

    for phrase, points in weights.items():
        if phrase in text:
            score += points

    # Competition bonuses
    competition_bonus = {
        "premier league": 14,
        "champions league": 18,
        "europa league": 10,
        "club world cup": 12,
        "world cup": 18,
        "la liga": 10,
        "serie a": 10,
        "bundesliga": 10,
        "ligue 1": 8,
    }
    for phrase, points in competition_bonus.items():
        if phrase in text:
            score += points

    # Big club / audience bonuses
    big_club_bonus = {
        "arsenal": 8,
        "chelsea": 8,
        "liverpool": 10,
        "manchester united": 12,
        "manchester city": 10,
        "tottenham": 7,
        "spurs": 7,
        "barcelona": 10,
        "barca": 10,
        "real madrid": 12,
        "bayern": 9,
        "psg": 8,
        "juventus": 8,
        "inter milan": 7,
        "ac milan": 7,
    }
    for phrase, points in big_club_bonus.items():
        if phrase in text:
            score += points

    # Headline bonus
    headline = title.lower()
    if any(word in headline for word in ["breaking", "official", "sacked", "injury", "here we go"]):
        score += 10

    # Slight penalty for bland preview-type stories
    bland_terms = [
        "preview", "training", "schedule", "press conference",
        "ticket", "live blog", "how to watch"
    ]
    for term in bland_terms:
        if term in text:
            score -= 12

    return score


def generate_ai_script(article_title, summary):
    prompt = f"""
Write a YouTube Short script about this football story.

TITLE:
{article_title}

DETAILS:
{summary}

Rules:
- Keep it under 130 words
- No emojis
- Do not sound robotic
- Do not be overly corny
- Sound like a sharp football fan talking fast on TikTok or YouTube Shorts
- If the details are short, use recent form, rivalry, stakes, or fan reaction to make it more interesting
- Be specific and vivid, but do not make up fake facts

Structure:
1. Strong opening hook
2. Explain the story clearly
3. Give one opinionated takeaway
4. End with a question for comments

Do not label sections as HOOK, THE TEA, HOT TAKE, or QUESTION.
""".strip()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a football YouTube Shorts scriptwriter. Write short, punchy, natural scripts with good flow."
            },
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.strip()


def post_script(article, script):
    message = f"""⚽ **FOOTYBOT SCRIPT**

**Source:** {article['source']}
**Topic:** {article['title']}
**Heat Score:** {article['heat_score']}
**Link:** {article['link']}

```text
{script}
```"""
    post_to_discord(message)


if __name__ == "__main__":
    sources = load_sources("sourses.txt")
    seen_links = get_seen_links()

    all_potential_articles = []

    for url in sources:
        try:
            articles = fetch_articles(url, limit=10)
        except Exception as e:
            print(f"Failed to read feed: {url}")
            print(f"Error: {e}")
            continue

        for article in articles:
            if article["link"] in seen_links:
                continue

            if not is_soccer_story(article["title"], article["summary"]):
                continue

            article["heat_score"] = get_heat_score(article["title"], article["summary"])
            all_potential_articles.append(article)

    if not all_potential_articles:
        print("No new soccer stories found.")
    else:
        ranked_articles = sorted(
            all_potential_articles,
            key=lambda x: x["heat_score"],
            reverse=True
        )

        for article in ranked_articles[:3]:
            try:
                script = generate_ai_script(article["title"], article["summary"])
                post_script(article, script)
                add_seen_link(article["link"])
                print(f"Posted: {article['title']} (Score: {article['heat_score']})")
            except Exception as e:
                print(f"Failed to process: {article['title']}")
                print(f"Error: {e}")