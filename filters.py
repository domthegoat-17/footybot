import calendar
import hashlib
import re
from datetime import datetime, timezone

from config import (
    NFL_TERMS, SOCCER_TERMS, CLUBS_AND_NATIONS,
    HEAT_WEIGHTS, COMPETITION_BONUS, BIG_CLUB_BONUS,
    HEADLINE_BONUS_TERMS, HEADLINE_BONUS,
    BLAND_TERMS, BLAND_PENALTY,
    RECENCY_BONUSES, TREND_BONUSES,
    SIMILARITY_THRESHOLD,
)

# Safe aliases only — must be unambiguous shorthands
_ALIASES = {
    "atletico": "atletico madrid",
    "barca":    "barcelona",
    "spurs":    "tottenham",
}

_ENTITY_TERMS = (
    set(CLUBS_AND_NATIONS)
    | set(COMPETITION_BONUS.keys())
    | set(_ALIASES.keys())
    | {
        "injury", "injured", "transfer", "sacked", "signing", "ban",
        "suspension", "red card", "hat-trick", "relegation", "final",
        "semi-final", "derby", "here we go", "confirmed", "appointed",
        "medical", "release clause", "ruled out", "comeback", "record",
    }
)

_STOP_WORDS = {
    "the", "a", "an", "in", "on", "at", "of", "to", "and", "for",
    "is", "are", "was", "as", "by", "with", "his", "her", "their",
    "he", "she", "it", "its", "from", "after", "before", "about",
    "into", "that", "this", "but", "not", "be", "has", "have",
}

_PUNCT = str.maketrans("", "", ".,!?:;\"'()-")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_word(w: str) -> str:
    return w.translate(_PUNCT).lower()


def _tokenize(s: str) -> set:
    """Lowercase, strip punctuation first, then filter stop words."""
    tokens = set()
    for w in s.lower().split():
        cleaned = _clean_word(w)
        if cleaned and cleaned not in _STOP_WORDS and len(cleaned) > 2:
            tokens.add(cleaned)
    return tokens


def _word_boundary_match(term: str, text: str) -> bool:
    """
    Match term in text respecting word boundaries.
    Multi-word terms use simple substring (already space-separated).
    Single-word terms use regex word boundary to avoid partial matches.
    """
    if " " in term:
        return term in text
    return bool(re.search(r'\b' + re.escape(term) + r'\b', text))


# ---------------------------------------------------------------------------
# Entity extraction — shared by within-run and cross-run matching
# ---------------------------------------------------------------------------

def extract_entities(title: str) -> set:
    """
    Extracts known meaningful entities from a title using word-boundary
    matching. Aliases are resolved to canonical form.
    Returns a set of canonical entity strings.
    """
    text = title.lower()
    found = set()
    # Longest terms first so "manchester united" is matched before "united"
    for term in sorted(_ENTITY_TERMS, key=len, reverse=True):
        if _word_boundary_match(term, text):
            canonical = _ALIASES.get(term, term)
            found.add(canonical)
            # Mask so sub-terms don't double-match
            text = text.replace(term, " ")
    return found


def make_fingerprint(title: str) -> str:
    """
    Entity-based fingerprint, falls back to token sort when < 2 entities found.
    """
    entities = extract_entities(title)

    if len(entities) >= 2:
        key = " ".join(sorted(entities))
    else:
        tokens = []
        for w in title.lower().split():
            cleaned = _clean_word(w)
            if cleaned and cleaned not in _STOP_WORDS and len(cleaned) > 2:
                tokens.append(cleaned)
        key = " ".join(sorted(tokens))

    return hashlib.md5(key.encode()).hexdigest()[:10]


# ---------------------------------------------------------------------------
# Similarity — entity-first, Jaccard fallback
# ---------------------------------------------------------------------------

def _jaccard(a: str, b: str) -> int:
    sa, sb = _tokenize(a), _tokenize(b)
    if not sa or not sb:
        return 0
    return int(len(sa & sb) / len(sa | sb) * 100)


def topic_similarity(a: str, b: str) -> int:
    """
    Entity overlap when both titles have 2+ entities, Jaccard fallback otherwise.
    """
    ea, eb = extract_entities(a), extract_entities(b)
    if len(ea) >= 2 and len(eb) >= 2:
        return int(len(ea & eb) / len(ea | eb) * 100)
    return _jaccard(a, b)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def is_soccer_story(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    if any(term in text for term in NFL_TERMS):
        return False
    return any(term in text for term in SOCCER_TERMS) or any(team in text for team in CLUBS_AND_NATIONS)


def get_recency_bonus(published) -> int:
    if not published:
        return 0
    try:
        # calendar.timegm treats the tuple as UTC, which is correct for RSS feeds
        pub_dt = datetime.fromtimestamp(calendar.timegm(published), tz=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
        for max_hours, bonus in RECENCY_BONUSES:
            if age_hours <= max_hours:
                return bonus
    except Exception:
        pass
    return 0


def get_heat_score(title: str, summary: str, published=None) -> int:
    text = (title + " " + summary).lower()
    score = 0

    for phrase, points in HEAT_WEIGHTS.items():
        if phrase in text:
            score += points
    for phrase, points in COMPETITION_BONUS.items():
        if phrase in text:
            score += points
    for phrase, points in BIG_CLUB_BONUS.items():
        if phrase in text:
            score += points
    if any(word in title.lower() for word in HEADLINE_BONUS_TERMS):
        score += HEADLINE_BONUS
    for term in BLAND_TERMS:
        if term in text:
            score += BLAND_PENALTY

    score += get_recency_bonus(published)
    return score


# ---------------------------------------------------------------------------
# Grouping and trend detection
# ---------------------------------------------------------------------------

def group_by_topic(articles: list[dict]) -> list[list[dict]]:
    """
    Groups articles covering the same story.
    Compares each candidate against ALL articles already in a group,
    not just the seed — catches chain matches (A~B, B~C, A not~C).
    """
    groups = []
    used = set()

    for i, article in enumerate(articles):
        if i in used:
            continue

        group = [article]
        used.add(i)

        for j, other in enumerate(articles):
            if j in used:
                continue
            # Match against any member already in the group
            if any(
                topic_similarity(member["title"], other["title"]) >= SIMILARITY_THRESHOLD
                for member in group
            ):
                group.append(other)
                used.add(j)

        groups.append(group)

    return groups


def apply_trend_bonus(articles: list[dict]) -> list[dict]:
    """
    Groups by topic, applies trend bonus by unique source count,
    deduplicates to the highest-scoring article per group.
    TREND_BONUSES is sorted descending at runtime so config order doesn't matter.
    """
    groups = group_by_topic(articles)
    result = []

    # Sort descending so the first match is always the highest applicable bonus
    sorted_bonuses = sorted(TREND_BONUSES, key=lambda x: x[0], reverse=True)

    for group in groups:
        source_count = len({a["source"] for a in group})

        trend_bonus = 0
        for min_sources, bonus in sorted_bonuses:
            if source_count >= min_sources:
                trend_bonus = bonus
                break

        if trend_bonus > 0:
            print(f"Trend detected ({source_count} sources, +{trend_bonus}): {group[0]['title']}")

        for article in group:
            article["heat_score"] += trend_bonus
            article["trend_count"] = source_count

        best = max(group, key=lambda x: x["heat_score"])
        result.append(best)

    return result