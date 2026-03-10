from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = (
    "You are a football content creator who makes viral YouTube Shorts. "
    "You are opinionated, fast-talking, and slightly unhinged — like someone "
    "who lives on football Twitter and has strong takes on everything. "
    "You write for fans, not journalists. You take sides. You sound real."
)

USER_PROMPT_TEMPLATE = """
You are generating a YouTube Shorts content package about this football story.

TITLE:
{title}

DETAILS:
{summary}

---

Produce output in this EXACT format with these EXACT labels.
Each section must start with its label on its own line.
Hooks must be exactly 3 lines, each starting with "1.", "2.", "3." — no sub-points, no indenting.

TITLE:
[A short punchy video title. Specific, not vague. No clickbait fluff.]

HOOKS:
1. [Shocking or counterintuitive angle — one sentence]
2. [Lead with a stat or number — one sentence]
3. [Fan emotion or stakes — one sentence]

SCRIPT:
[The full spoken script. Around 120 words. No labels, no headers — just the spoken words.

The script must:
- Write a completely original opening sentence — do NOT copy any hook line word for word.
  The hook lines are inspiration only. Rephrase the angle in a fresh way.
- Do not open with a club name or player name. Start with the situation, the stakes, or the absurdity.
- Include at least one specific number or statistic naturally in the body.
  Use stats from the article if available. Otherwise infer: years since last achievement,
  number of meetings between clubs, recent record, table position, appearances.
- Build toward one sharp committed opinion. Take a clear side.
  Structure: FACT then EMOTIONAL FRAMING then COMMON TAKE then one closing question.
- End with a single question that divides fans and starts arguments.

Rules:
- No emojis
- No exclamation marks
- Do not start consecutive sentences with the same word
- Never use: momentum, magic of the cup, fairytale, at the end of the day, to be fair,
  big news from, football fans everywhere, huge clash, everyone was hoping for
- Use emotional words where they fit: panic, collapse, pressure, chaos, fuming,
  disaster, meltdown, shock — but never exaggerate beyond the facts
- One angle only. Ignore secondary details unless they strengthen the main story
- Be specific. Generic scripts are forgettable.]
""".strip()


def generate_ai_script(article_title: str, summary: str) -> dict:
    """Returns a dict with keys: title, hooks, script, raw."""
    prompt = USER_PROMPT_TEMPLATE.format(title=article_title, summary=summary)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    raw = response.choices[0].message.content.strip()
    return _parse_output(raw)


def _parse_output(raw: str) -> dict:
    sections = {
        "title": "",
        "hooks": [],
        "script": "",
        "raw": raw,
    }

    current = None
    buffer = []

    for line in raw.splitlines():
        stripped = line.strip()

        if stripped.upper().startswith("TITLE:"):
            if current and buffer:
                _flush(sections, current, buffer)
            current = "title"
            inline = stripped[6:].strip()
            buffer = [inline] if inline else []

        elif stripped.upper().startswith("HOOKS:"):
            if current and buffer:
                _flush(sections, current, buffer)
            current = "hooks"
            buffer = []

        elif stripped.upper().startswith("SCRIPT:"):
            if current and buffer:
                _flush(sections, current, buffer)
            current = "script"
            inline = stripped[7:].strip()
            buffer = [inline] if inline else []

        else:
            if stripped:
                # For hooks: only collect lines that start with a digit
                # This prevents indented continuation lines becoming extra hooks
                if current == "hooks":
                    if stripped[0].isdigit():
                        buffer.append(stripped)
                    elif buffer:
                        # Continuation of the last hook — append to it
                        buffer[-1] = buffer[-1] + " " + stripped
                else:
                    buffer.append(stripped)

    if current and buffer:
        _flush(sections, current, buffer)

    return sections


def _flush(sections: dict, key: str, buffer: list) -> None:
    if key == "hooks":
        hooks = []
        for line in buffer:
            # Strip leading "1." "2." "3." numbering
            cleaned = line.lstrip("0123456789.-) ").strip()
            if cleaned:
                hooks.append(cleaned)
        sections["hooks"] = hooks
    elif key in sections:
        sections[key] = "\n".join(line for line in buffer if line)