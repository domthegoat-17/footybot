"""
knowledge_extractor.py
 
Makes a lightweight GPT call to extract structured intel from a raw article.
Only three categories are kept: transfer, injury, drama.
Anything else returns category="skip" and is not saved to the knowledge store.
"""
 
import json
from openai import OpenAI
 
client = OpenAI()
 
# Only these three categories get stored
VALID_CATEGORIES = {"transfer", "injury", "drama"}
 
_SYSTEM = (
    "You are a football news analyst. Extract structured data from article snippets. "
    "Respond ONLY with a valid JSON object. No markdown, no explanation, no extra text."
)
 
_USER_TEMPLATE = """Extract structured intel from this football article.
 
TITLE: {title}
SUMMARY: {summary}
 
Return a JSON object with exactly these keys:
 
{{
  "category": one of "transfer" | "injury" | "drama" | "skip",
  "player": player name as a string, or null if not applicable,
  "from_club": club the player is leaving, or null,
  "to_club": club the player is joining, or null,
  "fee": transfer fee as a string (e.g. "£45m", "free", "loan"), or null,
  "is_rumour": true if this is unconfirmed (linked, eyeing, interested, could join), false if confirmed/official,
  "status": one of "rumour" | "advanced" | "official" | null (null for non-transfers),
  "key_fact": a single sentence summarising the most important fact in this article
}}
 
Category rules — be generous, lean toward a real category over skip:
- "transfer": any signing, sale, loan, release, bid, fee, or transfer rumour.
  Includes: "linked with", "set to join", "close to signing", "eyeing", "approach made".
  Set status: "rumour" for links/interest, "advanced" for negotiations/medical/bid accepted, "official" for confirmed signings.
- "injury": any player injury, fitness doubt, ruled out, or return from injury.
- "drama": ONLY on-pitch incidents — red cards, bans, suspensions, last-minute goals, comebacks.
  Do NOT use drama for manager sackings, press conferences, or off-pitch controversy.
- "skip": match previews, fixture lists, how-to-watch guides, training updates, press conferences,
  manager sackings, managerial appointments, ticket news, opinion columns, rankings, awards.
 
When in doubt between a real category and skip, choose the real category.
 
For transfers: extract fee if mentioned (£40m, €55m, free, loan, undisclosed). Use full club names.""".strip()
 
 
def extract_intel(title: str, summary: str) -> dict:
    """
    Returns a dict with keys: category, player, from_club, to_club, fee, key_fact.
    category="skip" means this article should not be stored.
    """
    prompt = _USER_TEMPLATE.format(title=title, summary=summary[:600])
 
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=300,
            temperature=0,
        )
 
        raw = response.choices[0].message.content.strip()
 
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
 
        intel = json.loads(raw)
 
        category = intel.get("category", "skip")
        intel["category"] = category if category in VALID_CATEGORIES else "skip"
 
        for key in ("player", "from_club", "to_club", "fee", "is_rumour", "status", "key_fact"):
            intel.setdefault(key, None)
        # is_rumour should be bool, not None
        if intel["is_rumour"] is None:
            intel["is_rumour"] = False
 
        if not intel.get("key_fact"):
            intel["key_fact"] = title
 
        return intel
 
    except Exception as e:
        print(f"  [extractor] Failed for '{title}': {e}")
        return {
            "category":  _fallback_category(title),
            "player":    None,
            "from_club": None,
            "to_club":   None,
            "fee":       None,
            "is_rumour": False,
            "status":    None,
            "key_fact":  title,
        }
 
 
def _fallback_category(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["transfer", "signing", "bid", "deal", "loan", "fee", "joins", "linked", "eyeing"]):
        return "transfer"
    if any(w in t for w in ["injur", "doubt", "ruled out", "fitness", "return"]):
        return "injury"
    if any(w in t for w in ["red card", "ban", "suspended", "comeback", "last-minute", "stoppage time"]):
        return "drama"
    return "skip"