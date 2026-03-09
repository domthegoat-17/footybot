NFL_TERMS = [
    "nfl", "touchdown", "touchdowns", "quarterback", "super bowl",
    "interception", "gridiron", "wide receiver", "linebacker"
]

SOCCER_TERMS = [
    "football", "soccer", "premier league", "champions league",
    "europa league", "conference league", "club world cup",
    "transfer", "la liga", "serie a", "bundesliga", "ligue 1",
    "fifa", "uefa", "goal", "hat-trick", "relegation",
    "ballon d'or", "manager", "striker", "midfielder", "defender",
    "goalkeeper", "penalty", "red card", "clean sheet", "fixture"
]

CLUBS_AND_NATIONS = [
    "arsenal", "chelsea", "liverpool", "manchester united",
    "manchester city", "tottenham", "spurs", "newcastle",
    "aston villa", "barcelona", "barca", "real madrid",
    "atletico madrid", "bayern", "dortmund", "juventus",
    "inter milan", "ac milan", "napoli", "psg",
    "england", "france", "spain", "portugal", "brazil",
    "argentina", "germany", "italy", "netherlands"
]

HEAT_WEIGHTS = {
    # Huge engagement
    "here we go": 40,
    "breaking": 25,
    "exclusive": 22,
    "official": 20,
    "confirmed": 18,

    # Transfer / manager chaos
    "transfer": 18,
    "bid": 12,
    "medical": 16,
    "deal": 12,
    "signing": 14,
    "loan": 10,
    "release clause": 16,
    "sacked": 24,
    "manager": 8,
    "appointed": 14,

    # Drama / controversy
    "controversy": 18,
    "drama": 14,
    "row": 12,
    "clash": 12,
    "fuming": 14,
    "slammed": 12,
    "angry": 10,
    "ban": 16,
    "suspension": 16,

    # Match chaos / moments
    "injury": 18,
    "injured": 18,
    "red card": 16,
    "penalty": 10,
    "comeback": 16,
    "stoppage time": 12,
    "last-minute": 14,
    "winner": 10,
    "equaliser": 8,
    "hat-trick": 14,
    "record": 12,
    "historic": 16,

    # Stakes
    "title race": 18,
    "relegation": 16,
    "knockout": 14,
    "semi-final": 14,
    "final": 18,
    "derby": 18,

    # Injuries before big moments
    "doubt": 10,
    "ruled out": 16,
    "miss": 8,
}

COMPETITION_BONUS = {
    "premier league": 14,
    "champions league": 18,
    "europa league": 10,
    "club world cup": 12,
    "world cup": 18,
    "la liga": 10,
    "serie a": 10,
    "bundesliga": 10,
    "ligue 1": 8,
}

BIG_CLUB_BONUS = {
    "arsenal": 8,
    "chelsea": 8,
    "liverpool": 10,
    "manchester united": 12,
    "manchester city": 10,
    "tottenham": 7,
    "spurs": 7,
    "barcelona": 10,
    "barca": 10,
    "real madrid": 12,
    "bayern": 9,
    "psg": 8,
    "juventus": 8,
    "inter milan": 7,
    "ac milan": 7,
}

HEADLINE_BONUS_TERMS = ["breaking", "official", "sacked", "injury", "here we go"]
HEADLINE_BONUS = 10

BLAND_TERMS = [
    "preview", "training", "schedule", "press conference",
    "ticket", "live blog", "how to watch"
]
BLAND_PENALTY = -12

# Recency bonuses (in hours)
RECENCY_BONUSES = [
    (2, 15),   # published within 2 hours → +15
    (6, 8),    # published within 6 hours → +8
]

# Trend detection bonuses (number of sources covering same story)
TREND_BONUSES = [
    (4, 40),   # 4+ sources → +40
    (3, 25),   # 3 sources → +25
    (2, 15),   # 2 sources → +15
]

# Minimum heat score to be considered for posting
HEAT_THRESHOLD = 40

# Fuzzy match threshold for duplicate/trend detection (0-100)
SIMILARITY_THRESHOLD = 65