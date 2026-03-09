from feed_reader import load_sources, fetch_articles, fetch_full_content, SUMMARY_MIN_LENGTH
from filters import is_soccer_story, get_heat_score, apply_trend_bonus
from script_generator import generate_ai_script
from tracker import get_seen, add_seen, prune_seen, make_fingerprint
from discord_post import post_to_discord
from config import HEAT_THRESHOLD


def post_script(article: dict, script: str) -> None:
    trend_line = f"**Trending:** {article['trend_count']} sources covering this\n" if article.get("trend_count", 1) > 1 else ""
    message = f"""⚽ **FOOTYBOT SCRIPT**

**Source:** {article['source']}
**Topic:** {article['title']}
**Heat Score:** {article['heat_score']}
{trend_line}**Link:** {article['link']}

```text
{script}
```"""
    post_to_discord(message)


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
            # Skip if exact link already seen
            if article["link"] in seen_links:
                continue

            # Skip if same story already covered (different outlet, same topic)
            fingerprint = make_fingerprint(article["title"])
            if fingerprint in seen_fingerprints:
                print(f"Skipping duplicate topic: {article['title']}")
                continue

            if not is_soccer_story(article["title"], article["summary"]):
                continue

            # Only scrape full content after passing all filters
            if len(article["summary"]) < SUMMARY_MIN_LENGTH:
                print(f"Short summary, fetching full content: {article['title']}")
                full_text = fetch_full_content(article["link"])
                if full_text:
                    article["summary"] = full_text

            article["heat_score"] = get_heat_score(article["title"], article["summary"], article.get("published"))
            all_potential_articles.append(article)

    if not all_potential_articles:
        print("No new soccer stories found.")
    else:
        # Apply trend bonuses and deduplicate same-story articles within this run
        all_potential_articles = apply_trend_bonus(all_potential_articles)

        # Filter out low-scoring junk
        all_potential_articles = [a for a in all_potential_articles if a["heat_score"] >= HEAT_THRESHOLD]

        if not all_potential_articles:
            print(f"No articles passed the heat threshold ({HEAT_THRESHOLD}).")
        else:
            ranked_articles = sorted(all_potential_articles, key=lambda x: x["heat_score"], reverse=True)

            for article in ranked_articles[:3]:
                try:
                    print(f"Generating script for: {article['title']}")
                    script = generate_ai_script(article["title"], article["summary"])
                    print(f"Posting to Discord...")
                    post_script(article, script)
                    add_seen(article["link"], article["title"])
                    print(f"Posted: {article['title']} (Score: {article['heat_score']})")
                except Exception as e:
                    print(f"Failed to process: {article['title']}")
                    print(f"Error: {e}")
                    