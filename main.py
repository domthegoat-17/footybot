from feed_reader import load_sources, fetch_articles, fetch_full_content, SUMMARY_MIN_LENGTH
from filters import is_soccer_story, get_heat_score, apply_trend_bonus
from script_generator import generate_ai_script
from script_formatter import format_for_shorts
from tracker import get_seen, add_seen, prune_seen, make_fingerprint
from discord_post import post_to_discord
from config import HEAT_THRESHOLD

SEPARATOR = "─" * 40


def _format_flags(article: dict) -> str:
    flags = []
    if article.get("trend_count", 1) == 1:
        flags.append("single source")
    if len(article.get("summary", "")) < 300:
        flags.append("weak summary")
    if article["heat_score"] < 55:
        flags.append("low heat")
    return "  ".join(f"⚠ {f}" for f in flags) if flags else "none"


def post_script(article: dict, content: dict) -> None:
    trend_count = article.get("trend_count", 1)
    sources_line = f"{trend_count} source{'s' if trend_count != 1 else ''}"
    if trend_count > 1:
        sources_line += " — trending"

    hooks_text = "\n".join(
        f"{i+1}. {h}" for i, h in enumerate(content.get("hooks", []))
    )

    original_script = content.get("script") or content.get("raw", "")
    shorts_script = format_for_shorts(original_script)

    # Message 1: metadata + hooks + original script
    msg1 = f"""⚽ **FOOTYBOT**

**Topic:** {article['title']}
**Heat Score:** {article['heat_score']}  |  **Sources:** {sources_line}
**Flags:** {_format_flags(article)}

**Suggested Title:**
{content.get('title', '—')}

**Hook Options:**
{hooks_text}

{SEPARATOR}
**ORIGINAL SCRIPT**
{SEPARATOR}
{original_script}
{SEPARATOR}
**Link:** {article['link']}"""

    # Message 2: shorts script only — clean copy-paste block
    msg2 = f"""{SEPARATOR}
**SHORTS SCRIPT**
{SEPARATOR}
{shorts_script}
{SEPARATOR}"""

    post_to_discord(msg1)
    post_to_discord(msg2)


if __name__ == "__main__":
    sources = load_sources("sources.txt")

    pruned = prune_seen()
    if pruned:
        print(f"Pruned {pruned} old entries from seen_links.txt")

    seen_links, seen_fingerprints = get_seen()
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

            fingerprint = make_fingerprint(article["title"])
            if fingerprint in seen_fingerprints:
                print(f"Skipping duplicate topic: {article['title']}")
                continue

            if not is_soccer_story(article["title"], article["summary"]):
                continue

            if len(article["summary"]) < SUMMARY_MIN_LENGTH:
                print(f"Short summary, fetching full content: {article['title']}")
                full_text = fetch_full_content(article["link"])
                if full_text:
                    article["summary"] = full_text

            article["heat_score"] = get_heat_score(
                article["title"], article["summary"], article.get("published")
            )
            all_potential_articles.append(article)

    if not all_potential_articles:
        print("No new soccer stories found.")
    else:
        all_potential_articles = apply_trend_bonus(all_potential_articles)

        print(f"\n--- {len(all_potential_articles)} articles after trend grouping ---")
        for a in sorted(all_potential_articles, key=lambda x: x["heat_score"], reverse=True):
            print(f"  [{a['heat_score']}] {a['title']}")
        print()

        all_potential_articles = [
            a for a in all_potential_articles if a["heat_score"] >= HEAT_THRESHOLD
        ]

        if not all_potential_articles:
            print(f"No articles passed the heat threshold ({HEAT_THRESHOLD}).")
        else:
            ranked_articles = sorted(
                all_potential_articles, key=lambda x: x["heat_score"], reverse=True
            )

            for article in ranked_articles[:3]:
                try:
                    print(f"Generating script for: {article['title']}")
                    content = generate_ai_script(article["title"], article["summary"])
                    print("Posting to Discord...")
                    post_script(article, content)
                    add_seen(article["link"], article["title"])
                    print(f"Posted: {article['title']} (Score: {article['heat_score']})")
                except Exception as e:
                    print(f"Failed to process: {article['title']}")
                    print(f"Error: {e}")