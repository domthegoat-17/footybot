import time
from feed_reader import load_sources, fetch_articles, fetch_full_content, SUMMARY_MIN_LENGTH
from filters import is_soccer_story, get_heat_score, apply_trend_bonus
from script_generator import generate_ai_script
from script_formatter import format_for_shorts
from tracker import get_seen, add_seen, prune_seen, make_fingerprint
from discord_post import post_to_discord
from config import HEAT_THRESHOLD
from knowledge_store import get_known_ids, add_entry, prune_store, store_summary, entry_id
from knowledge_extractor import extract_intel
 
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
 
 
RUN_INTERVAL_SECONDS = 3600  # 1 hour
 
 
def run_once(sources: list[str]) -> None:
    # --- Prune old entries ---
    pruned_seen = prune_seen()
    if pruned_seen:
        print(f"Pruned {pruned_seen} old entries from seen_links.txt")
 
    pruned_knowledge = prune_store()
    if pruned_knowledge:
        print(f"Pruned {pruned_knowledge} old entries from knowledge store")
 
    print(store_summary())
    print()
 
    seen_links, seen_fingerprints = get_seen()
    known_ids = get_known_ids()  # links already in the knowledge store
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
 
        # ----------------------------------------------------------------
        # KNOWLEDGE STORE POPULATION
        # Extract and store intel from ALL qualifying articles, regardless
        # of whether they pass the heat threshold or get posted.
        # This gives the roundup a richer pool to draw from.
        # ----------------------------------------------------------------
        print("--- Extracting intel for knowledge store ---")
        stored_count = 0
        skipped_count = 0
        for article in all_potential_articles:
            if entry_id(article["link"]) in known_ids:
                continue  # already extracted on a previous run
            try:
                intel = extract_intel(article["title"], article["summary"])
                category = intel.get("category", "skip")
                if category == "skip":
                    skipped_count += 1
                    continue  # not a transfer, injury, or drama — discard
                add_entry(article, intel)
                stored_count += 1
                key_fact = intel.get("key_fact", "")
                print(f"  [{category}] {key_fact[:80]}")
            except Exception as e:
                print(f"  Failed to extract intel for: {article['title']} — {e}")
 
        if stored_count:
            print(f"Stored {stored_count} new entries ({skipped_count} skipped).")
        else:
            print(f"No new entries to store ({skipped_count} skipped as irrelevant).")
        print()
 
        # ----------------------------------------------------------------
        # Normal pipeline: filter by heat, generate scripts, post to Discord
        # ----------------------------------------------------------------
        qualifying = [
            a for a in all_potential_articles if a["heat_score"] >= HEAT_THRESHOLD
        ]
 
        if not qualifying:
            print(f"No articles passed the heat threshold ({HEAT_THRESHOLD}).")
        else:
            ranked_articles = sorted(
                qualifying, key=lambda x: x["heat_score"], reverse=True
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
 
 
def _clear_knowledge_store() -> None:
    """Wipes knowledge.json completely. Called at midnight EST each day."""
    from pathlib import Path
    path = Path("knowledge.json")
    if path.exists():
        path.write_text("[]", encoding="utf-8")
        print("Knowledge store cleared for the new day.")
 
 
def _next_midnight_est() -> float:
    """Returns seconds until the next midnight EST."""
    from datetime import datetime, timezone, timedelta
    EST = timezone(timedelta(hours=-5))
    now_est = datetime.now(EST)
    midnight_est = (now_est + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (midnight_est - now_est).total_seconds()
 
 
if __name__ == "__main__":
    from datetime import datetime, timezone, timedelta
    EST = timezone(timedelta(hours=-5))
 
    sources = load_sources("sources.txt")
    print("FootyBot started. Press Ctrl+C at any time to stop.\n")
 
    # Track which EST date we last cleared on so we only clear once per day
    last_cleared_date = datetime.now(EST).date()
 
    try:
        while True:
            now_est = datetime.now(EST)
 
            # Clear knowledge store at midnight EST (once per day)
            if now_est.date() > last_cleared_date:
                _clear_knowledge_store()
                last_cleared_date = now_est.date()
 
            print(f"{'=' * 40}")
            print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (local)")
            print(f"EST: {now_est.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 40}\n")
 
            run_once(sources)
 
            print(f"\nNext run in {RUN_INTERVAL_SECONDS // 60} minutes. Press Ctrl+C to stop.")
            time.sleep(RUN_INTERVAL_SECONDS)
 
    except KeyboardInterrupt:
        print("\n\nFootyBot stopped. Goodbye.")