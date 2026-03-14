"""
roundup.py
 
Generates a YouTube Shorts roundup script from stored knowledge intel.
 
Usage:
    python roundup.py transfers
    python roundup.py injuries
    python roundup.py drama
"""
 
import sys
from openai import OpenAI
from knowledge_store import get_entries, store_summary
from script_formatter import format_for_shorts
from discord_post import post_to_discord
 
client = OpenAI()
SEPARATOR = "─" * 40
 
# ---------------------------------------------------------------------------
# Category config
# ---------------------------------------------------------------------------
 
CATEGORY_CONFIG = {
    "transfers": {
        "store_key": "transfer",
        "label":     "Transfer Roundup",
        "emoji":     "💰",
    },
    "injuries": {
        "store_key": "injury",
        "label":     "Injury Update",
        "emoji":     "🚑",
    },
    "drama": {
        "store_key": "drama",
        "label":     "Drama Roundup",
        "emoji":     "🔥",
    },
}
 
# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
 
SYSTEM_PROMPT = (
    "You are a football news presenter making rapid-fire YouTube Shorts. "
    "You deliver football intel clearly and quickly — no opinions, no takes, no editorialising. "
    "You sound like someone reading transfer news aloud to their mates. "
    "Factual. Fast. Specific."
)
 
TRANSFER_PROMPT = """
You are writing a spoken script for a YouTube Shorts video covering the latest football transfer news.
 
Here is the raw intel to work from:
{intel_block}
 
---
 
Write a spoken script in this exact style. Study these examples carefully:
 
EXAMPLE 1:
Here are the latest transfer rumours. Man United, Liverpool and Man City are all showing interest in Camavinga with Real Madrid looking to sell for around 50 million euros. Chelsea have been showing interest in signing Calafiori. Erling Haaland has held talks with Barcelona but his agent has played down a move. Madrid are open to selling Julian Alvarez to Premier League sides for around 85 million pounds. Juventus want to sign Robert Lewandowski as a free transfer. Man City are leading the race to sign Elliot Anderson. Arsenal, Atletico Madrid and AC Milan have all shown interest in signing Leon Goretzka as a free agent.
 
EXAMPLE 2:
Footballers set to leave their clubs this summer. Jeremy Doku is not happy with his current role at Man City and he could look to leave with interest from Atletico Madrid, Real Madrid and Borussia Dortmund. Miles Lewis Skelly is also said to be unhappy with his current role with interest from Everton and Crystal Palace. Confirmed Yulin Brant will leave Dortmund as a free agent with Barcelona, Real Madrid and Aston Villa all showing interest. Brentford will look to cash in on Kevin Schade with Bayern Munich showing interest and Brentford wanting around 70 million euros.
 
EXAMPLE 3:
These are the most wanted players ahead of the summer transfer window. Kevin Schade has clubs like Bayern Munich, Inter, Chelsea, Napoli and Spurs competing for his signature. Brentford reportedly wants around 60 million pounds to sell him. Man City, Liverpool and Arsenal are all competing for Elliot Anderson with Forest wanting at least 80 million pounds. Several clubs like Arsenal, Man United and Liverpool have been showing interest in a player who could be set to leave PSG this summer.
 
---
 
Rules for your script — follow all of these exactly:
- Open with a short scene-setting line like "Here are the latest transfer rumours" or "These are the players set to leave their clubs this summer" or "Transfer news" — vary it, do not copy the examples word for word
- One story per sentence or two. No story gets more than two sentences.
- Format per story: [player] + [situation] + [clubs interested] + [fee if known]
- Use natural rumour language: "it's reported", "are showing interest in", "looks set to", "is said to be", "could look to leave", "confirmed"
- If a fee is known, always include it
- If multiple clubs are interested, list them all
- No opinions. No takes. No "this is huge". No editorialising whatsoever.
- No emojis
- No exclamation marks
- No bullet points — this is spoken continuous prose
- No intro fluff like "welcome back" or "hey guys"
- No outro or sign-off
- End abruptly after the last story, no closing sentence
- Around 150 words. Cover as many stories from the intel as possible.
 
OUTPUT FORMAT — use these exact labels:
 
TITLE:
[Short specific title naming players or clubs — e.g. "Transfer Rumours: Haaland, Camavinga & More" — no vague titles]
 
SCRIPT:
[The spoken script only — no headers, no bullets, no labels inside the script]
""".strip()
 
INJURY_PROMPT = """
You are writing a spoken script for a YouTube Shorts video covering the latest football injury news.
 
Here is the raw intel to work from:
{intel_block}
 
---
 
Rules:
- Open with a short line like "Here are the latest injury updates" or "These are the players set to miss out"
- One player per sentence. Cover as many as possible.
- Format: [player] + [injury/status] + [timeline if known] + [impact on club]
- Be specific about timing where possible: "out for six weeks", "ruled out for the season", "could return before the final"
- No opinions or editorialising
- No emojis, no exclamation marks, no bullet points
- No intro fluff, no outro
- End abruptly after the last story
- Around 120 words
 
OUTPUT FORMAT:
 
TITLE:
[Short specific title]
 
SCRIPT:
[The spoken script only]
""".strip()
 
DRAMA_PROMPT = """
You are writing a spoken script for a YouTube Shorts video covering the latest football drama and on-pitch incidents.
 
Here is the raw intel to work from:
{intel_block}
 
---
 
Rules:
- Open with a short line like "Here is the latest from around football" or "Drama in football this week"
- One incident per sentence or two. Cover as many as possible.
- Format: [player/club] + [what happened] + [consequence if known]
- Stick to facts. No opinions.
- No emojis, no exclamation marks, no bullet points
- No intro fluff, no outro
- End abruptly after the last story
- Around 120 words
 
OUTPUT FORMAT:
 
TITLE:
[Short specific title]
 
SCRIPT:
[The spoken script only]
""".strip()
 
PROMPT_MAP = {
    "transfer": TRANSFER_PROMPT,
    "injury":   INJURY_PROMPT,
    "drama":    DRAMA_PROMPT,
}
 
# ---------------------------------------------------------------------------
# Intel block builder
# ---------------------------------------------------------------------------
 
def _build_intel_block(entries: list[dict], category: str) -> str:
    lines = []
    for i, e in enumerate(entries, 1):
        if category == "transfer":
            parts = [f"{i}."]
            if e.get("player"):
                parts.append(e["player"])
            if e.get("from_club") and e.get("to_club"):
                parts.append(f"({e['from_club']} → {e['to_club']})")
            elif e.get("to_club"):
                parts.append(f"(→ {e['to_club']})")
            elif e.get("from_club"):
                parts.append(f"(leaving {e['from_club']})")
            if e.get("fee"):
                parts.append(f"Fee: {e['fee']}")
            if e.get("status"):
                parts.append(f"[{e['status']}]")
            parts.append(f"— {e['key_fact']}")
            lines.append(" ".join(parts))
        else:
            line = f"{i}. {e['key_fact']}"
            if e.get("player"):
                line += f" (Player: {e['player']})"
            lines.append(line)
 
    return "\n".join(lines)
 
# ---------------------------------------------------------------------------
# GPT generator
# ---------------------------------------------------------------------------
 
def generate_roundup(category_key: str, entries: list[dict]) -> dict:
    intel_block = _build_intel_block(entries, category_key)
    prompt_template = PROMPT_MAP[category_key]
    prompt = prompt_template.format(intel_block=intel_block)
 
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
 
    raw = response.choices[0].message.content.strip()
    return _parse_output(raw)
 
 
def _parse_output(raw: str) -> dict:
    sections = {"title": "", "script": "", "raw": raw}
    current = None
    buffer = []
 
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
 
        if stripped.upper().startswith("TITLE:"):
            if current and buffer:
                _flush(sections, current, buffer)
            current = "title"
            inline = stripped[6:].strip()
            buffer = [inline] if inline else []
 
        elif stripped.upper().startswith("SCRIPT:"):
            if current and buffer:
                _flush(sections, current, buffer)
            current = "script"
            inline = stripped[7:].strip()
            buffer = [inline] if inline else []
 
        else:
            buffer.append(stripped)
 
    if current and buffer:
        _flush(sections, current, buffer)
 
    return sections
 
 
def _flush(sections: dict, key: str, buffer: list) -> None:
    if key in sections:
        sections[key] = "\n".join(line for line in buffer if line)
 
# ---------------------------------------------------------------------------
# Discord posting
# ---------------------------------------------------------------------------
 
def post_roundup(config: dict, entries: list[dict], content: dict) -> None:
    emoji = config["emoji"]
    label = config["label"]
 
    original_script = content.get("script") or content.get("raw", "")
    shorts_script = format_for_shorts(original_script)
 
    # Compact list of stories used — truncate facts to keep within Discord limit
    seen_facts = set()
    sources_lines = []
    for e in entries:
        fact = e.get("key_fact", "")[:80]  # truncate long facts
        if fact not in seen_facts:
            sources_lines.append(f"• {fact}")
            seen_facts.add(fact)
 
    sources_block = "\n".join(sources_lines[:8])  # cap at 8 lines
 
    msg1 = f"""{emoji} **FOOTYBOT — {label.upper()}**
 
**Stories used:** {len(entries)}
**Suggested Title:** {content.get('title', '—')}
 
{SEPARATOR}
**STORIES IN THIS ROUNDUP**
{SEPARATOR}
{sources_block}
{SEPARATOR}"""
 
    msg2 = f"""{SEPARATOR}
**SCRIPT**
{SEPARATOR}
{original_script}
{SEPARATOR}"""
 
    msg3 = f"""{SEPARATOR}
**SHORTS SCRIPT**
{SEPARATOR}
{shorts_script}
{SEPARATOR}"""
 
    post_to_discord(msg1)
    post_to_discord(msg2)
    post_to_discord(msg3)
 
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
 
VALID_ARGS = list(CATEGORY_CONFIG.keys())
 
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].lower() not in VALID_ARGS:
        print(f"Usage: python roundup.py [{' | '.join(VALID_ARGS)}]")
        print()
        print(store_summary())
        sys.exit(1)
 
    arg = sys.argv[1].lower()
    config = CATEGORY_CONFIG[arg]
    store_key = config["store_key"]
 
    print(store_summary())
    print()
 
    entries = get_entries(category=store_key)
 
    if not entries:
        print(f"No '{store_key}' entries in the knowledge store yet.")
        print("Run main.py a few times to populate it first.")
        sys.exit(0)
 
    print(f"Found {len(entries)} '{store_key}' entries. Generating roundup...")
 
    top_entries = entries[:20]
    content = generate_roundup(store_key, top_entries)
    post_roundup(config, top_entries, content)
 
    print(f"Roundup posted to Discord ({len(top_entries)} stories).")