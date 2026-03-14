"""
knowledge_store.py
 
Manages knowledge.json — a persistent store of structured intel extracted
from football articles. Accumulates across hourly runs. Separate from
seen_links.txt (which prevents re-posting); this is for roundup synthesis.
 
Entry schema:
{
    "id":         str,          # MD5 of link
    "link":       str,
    "title":      str,
    "summary":    str,          # raw summary kept for roundup context
    "category":   str,          # "transfer" | "injury" | "drama"
    "player":     str | null,
    "from_club":  str | null,
    "to_club":    str | null,
    "fee":        str | null,   # e.g. "£45m" or null
    "is_rumour":  bool,         # True if unconfirmed/linked/eyeing
    "status":     str,          # "rumour" | "advanced" | "official" | null
    "key_fact":   str,          # one-sentence distillation
    "source":     str,
    "heat_score": int,
    "stored_at":  str,          # UTC ISO date "YYYY-MM-DD"
}
"""
 
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
 
KNOWLEDGE_FILE = "knowledge.json"
PRUNE_AFTER_DAYS = 7
DATE_FORMAT = "%Y-%m-%d"
 
 
# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
 
def _today() -> str:
    return datetime.now(timezone.utc).strftime(DATE_FORMAT)
 
 
def entry_id(link: str) -> str:
    """Public helper — returns a stable 12-char ID for a given link."""
    return hashlib.md5(link.encode()).hexdigest()[:12]
 
 
def _load() -> list[dict]:
    path = Path(KNOWLEDGE_FILE)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []
 
 
def _save(entries: list[dict]) -> None:
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
 
 
# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
 
def get_known_ids() -> set[str]:
    """Returns set of entry IDs already in the store (used to skip re-extraction)."""
    return {e["id"] for e in _load()}
 
 
def add_entry(article: dict, intel: dict) -> None:
    """
    Saves one structured intel entry to the store.
 
    article: the dict from feed_reader (must have link, title, summary, source, heat_score)
    intel:   the dict from knowledge_extractor (category, player, from_club, to_club, fee, key_fact)
    """
    eid = entry_id(article["link"])
    entries = _load()
 
    # Don't add duplicates
    if any(e["id"] == eid for e in entries):
        return
 
    entry = {
        "id":        eid,
        "link":      article["link"],
        "title":     article["title"],
        "summary":   article.get("summary", "")[:800],  # cap storage size
        "category":  intel.get("category", "other"),
        "player":    intel.get("player"),
        "from_club": intel.get("from_club"),
        "to_club":   intel.get("to_club"),
        "fee":       intel.get("fee"),
        "is_rumour": intel.get("is_rumour", False),
        "status":    intel.get("status"),
        "key_fact":  intel.get("key_fact", article["title"]),
        "source":    article.get("source", "Unknown"),
        "heat_score": article.get("heat_score", 0),
        "stored_at": _today(),
    }
 
    entries.append(entry)
    _save(entries)
 
 
def get_entries(category: str | None = None, days: int = PRUNE_AFTER_DAYS) -> list[dict]:
    """
    Returns stored entries, optionally filtered by category and recency.
    Sorted newest-first by stored_at, then heat_score descending.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = _load()
 
    results = []
    for e in entries:
        # Recency filter
        date_str = e.get("stored_at")
        if date_str:
            try:
                entry_date = datetime.strptime(date_str, DATE_FORMAT).replace(tzinfo=timezone.utc)
                if entry_date < cutoff:
                    continue
            except ValueError:
                pass
 
        # Category filter
        if category and e.get("category") != category:
            continue
 
        results.append(e)
 
    # Sort: newest date first, then heat_score desc within same date
    results.sort(key=lambda x: (x.get("stored_at", ""), x.get("heat_score", 0)), reverse=True)
    return results
 
 
def prune_store(days: int = PRUNE_AFTER_DAYS) -> int:
    """Remove entries older than `days` days. Returns count pruned."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = _load()
    kept = []
    pruned = 0
 
    for e in entries:
        date_str = e.get("stored_at")
        if date_str:
            try:
                entry_date = datetime.strptime(date_str, DATE_FORMAT).replace(tzinfo=timezone.utc)
                if entry_date >= cutoff:
                    kept.append(e)
                else:
                    pruned += 1
            except ValueError:
                kept.append(e)
        else:
            kept.append(e)
 
    _save(kept)
    return pruned
 
 
def store_summary() -> str:
    """Returns a quick human-readable summary of what's in the store."""
    entries = _load()
    if not entries:
        return "Knowledge store is empty."
 
    cats = {}
    for e in entries:
        c = e.get("category", "other")
        cats[c] = cats.get(c, 0) + 1
 
    lines = [f"Knowledge store: {len(entries)} entries"]
    for cat, count in sorted(cats.items()):
        lines.append(f"  {cat}: {count}")
    return "\n".join(lines)