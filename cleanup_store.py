"""
cleanup_store.py

One-off script to purge "other" entries from knowledge.json and
re-classify any drama entries that shouldn't be there (manager sackings, etc.).

Run once:
    python cleanup_store.py
"""

import json
from pathlib import Path

KNOWLEDGE_FILE = "knowledge.json"

# Drama entries containing these terms are manager/controversy related — drop them
DRAMA_REJECT_TERMS = [
    "sacked", "appointed", "manager", "press conference",
    "interview", "contract", "wages", "salary", "row",
    "controversy", "fuming", "slammed", "statement"
]

path = Path(KNOWLEDGE_FILE)
if not path.exists():
    print("knowledge.json not found.")
    exit()

with open(path, "r", encoding="utf-8") as f:
    entries = json.load(f)

before = len(entries)
kept = []
dropped = 0

for e in entries:
    category = e.get("category", "other")

    # Drop "other" entirely
    if category == "other":
        print(f"  DROP [other] {e['title'][:80]}")
        dropped += 1
        continue

    # Drop drama entries that are actually manager/controversy stories
    if category == "drama":
        text = (e.get("title", "") + " " + e.get("key_fact", "")).lower()
        if any(term in text for term in DRAMA_REJECT_TERMS):
            print(f"  DROP [drama/off-pitch] {e['title'][:80]}")
            dropped += 1
            continue

    kept.append(e)

with open(path, "w", encoding="utf-8") as f:
    json.dump(kept, f, indent=2, ensure_ascii=False)

print(f"\nDone. {before} entries → {len(kept)} kept, {dropped} removed.")

# Show what's left
cats = {}
for e in kept:
    c = e.get("category", "?")
    cats[c] = cats.get(c, 0) + 1
print("Remaining breakdown:")
for cat, count in sorted(cats.items()):
    print(f"  {cat}: {count}")
