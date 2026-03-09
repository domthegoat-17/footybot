from pathlib import Path
from datetime import datetime, timedelta, timezone

# make_fingerprint lives in filters so both within-run and cross-run
# deduplication use exactly the same logic
from filters import make_fingerprint

SEEN_LINKS_FILE = "seen_links.txt"
PRUNE_AFTER_DAYS = 3
DATE_FORMAT = "%Y-%m-%d"


def _today() -> str:
    return datetime.now(timezone.utc).strftime(DATE_FORMAT)


def _parse_line(line: str) -> dict | None:
    """
    Handles all three historical formats:
      new:    link fingerprint date
      legacy: link date
      older:  link
    """
    line = line.strip()
    if not line:
        return None
    parts = line.split()
    if len(parts) >= 3:
        return {"link": parts[0], "fingerprint": parts[1], "date": parts[2]}
    elif len(parts) == 2:
        return {"link": parts[0], "fingerprint": None, "date": parts[1]}
    else:
        return {"link": parts[0], "fingerprint": None, "date": None}


def get_seen(file_path: str = SEEN_LINKS_FILE) -> tuple[set, set]:
    """Returns (seen_links, seen_fingerprints)."""
    path = Path(file_path)
    if not path.exists():
        return set(), set()

    seen_links = set()
    seen_fingerprints = set()

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parsed = _parse_line(line)
            if not parsed:
                continue
            seen_links.add(parsed["link"])
            if parsed["fingerprint"]:
                seen_fingerprints.add(parsed["fingerprint"])

    return seen_links, seen_fingerprints


def add_seen(link: str, title: str, file_path: str = SEEN_LINKS_FILE) -> None:
    fingerprint = make_fingerprint(title)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{link} {fingerprint} {_today()}\n")


def prune_seen(file_path: str = SEEN_LINKS_FILE, days: int = PRUNE_AFTER_DAYS) -> int:
    """Remove entries older than `days` days. Returns count pruned."""
    path = Path(file_path)
    if not path.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = []
    pruned = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parsed = _parse_line(line)
            if not parsed:
                continue
            date_str = parsed["date"]
            if date_str:
                try:
                    link_date = datetime.strptime(date_str, DATE_FORMAT).replace(tzinfo=timezone.utc)
                    if link_date >= cutoff:
                        kept.append(line.strip())
                    else:
                        pruned += 1
                except ValueError:
                    kept.append(line.strip())
            else:
                kept.append(line.strip())

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))

    return pruned