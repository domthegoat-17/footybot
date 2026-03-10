import re


def format_for_shorts(script: str) -> str:
    """
    Converts a paragraph-style script into YouTube Shorts pacing format.
    Each sentence gets its own line with a blank line between for natural pausing.
    Long sentences are split at commas or 'but'.
    Sentences with numbers get an extra pause after them for emphasis.
    """
    sentences = re.split(r'(?<=[.!?])\s+', script.strip())
    lines = []

    for s in sentences:
        s = s.strip()
        if not s:
            continue

        # Fix weird spacing before punctuation
        s = re.sub(r"\s+([.,!?])", r"\1", s)

        # Sentences with numbers get extra emphasis
        if re.search(r"\d", s):
            lines.append(s)
            lines.append("")
            continue

        # Break long sentences at safer natural split points
        if len(s.split()) > 14:
            parts = re.split(r",\s*|\sbut\s", s, maxsplit=1)
            if len(parts) > 1:
                lines.append(parts[0].strip())
                lines.append("")
                lines.append(parts[1].strip())
                lines.append("")
                continue

        lines.append(s)
        lines.append("")

    # Remove repeated blank lines
    cleaned = []
    for line in lines:
        if not (cleaned and cleaned[-1] == "" and line == ""):
            cleaned.append(line)

    return "\n".join(cleaned).strip()