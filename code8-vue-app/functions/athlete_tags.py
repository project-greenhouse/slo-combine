"""Curated tag taxonomy for athlete cohort matching.

`Sports` and `Positions` are free-text in athlete_info. To group athletes
into comparison cohorts (Same Sport, Same Position), we extract canonical
tags via substring matching against curated lists. Admins can edit the
proposed tags via the Athletes Table tab.

Add new tags here as new sports/positions appear. Order doesn't matter.
"""

SPORTS_TAGS = [
    "football",
    "basketball",
    "soccer",
    "track",
    "baseball",
    "softball",
    "volleyball",
    "lacrosse",
    "wrestling",
    "swimming",
    "tennis",
    "golf",
    "rugby",
    "cross country",
    "flag football",
]

# Positions are namespaced by sport because abbreviations clash (e.g. "C" =
# center in football AND basketball). The tag is the canonical form to store.
POSITION_TAGS_BY_SPORT = {
    "football": [
        "qb", "rb", "wr", "te", "ol", "dl", "lb", "db",
        "k", "p", "safety", "corner", "linebacker",
        "running back", "wide receiver", "tight end", "quarterback",
        "offensive line", "defensive line", "guard", "tackle", "center",
    ],
    "basketball": [
        "pg", "sg", "sf", "pf", "c",
        "point guard", "shooting guard", "small forward",
        "power forward", "center", "guard", "forward", "post", "wing",
    ],
    "soccer": [
        "gk", "goalkeeper", "defender", "midfielder", "forward", "striker",
        "center back", "fullback", "winger",
    ],
    "track": [
        "sprinter", "distance", "hurdler", "jumper",
        "thrower", "discus", "shot put", "javelin",
        "100m", "200m", "400m", "800m", "1600m", "long jump",
        "high jump", "triple jump",
    ],
    "baseball": [
        "pitcher", "catcher", "infielder", "outfielder",
        "shortstop", "first base", "second base", "third base",
    ],
    "softball": [
        "pitcher", "catcher", "infielder", "outfielder",
        "shortstop", "first base", "second base", "third base",
    ],
    "volleyball": [
        "outside", "middle", "setter", "libero", "opposite",
        "right side", "outside hitter", "middle blocker",
    ],
}


def _norm(text):
    """Lowercase + strip whitespace for substring matching."""
    return (text or "").lower().strip()


def propose_sports_tags(sports_text):
    """Return a list of canonical sport tags found as substrings in free-text Sports."""
    if not sports_text:
        return []
    s = _norm(sports_text)
    found = []
    for tag in SPORTS_TAGS:
        if tag in s:
            found.append(tag)
    return found


def propose_position_tags(positions_text, sports_tags):
    """Return a list of canonical position tags. Looks up positions for each
    sport the athlete plays. Returns prefixed tags like 'football:qb' so the
    same abbreviation can mean different things across sports."""
    if not positions_text:
        return []
    p = _norm(positions_text)
    found = []
    # Always check all sport buckets the athlete is tagged with
    sports_to_check = sports_tags or list(POSITION_TAGS_BY_SPORT.keys())
    seen = set()
    for sport in sports_to_check:
        if sport not in POSITION_TAGS_BY_SPORT:
            continue
        for pos in POSITION_TAGS_BY_SPORT[sport]:
            # Match on word boundaries for short abbreviations (qb, rb) to avoid
            # false matches inside longer words.
            if len(pos) <= 3:
                import re
                if re.search(rf"(^|[^a-z]){re.escape(pos)}([^a-z]|$)", p):
                    tag = f"{sport}:{pos}"
                    if tag not in seen:
                        seen.add(tag)
                        found.append(tag)
            else:
                if pos in p:
                    tag = f"{sport}:{pos}"
                    if tag not in seen:
                        seen.add(tag)
                        found.append(tag)
    return found


def age_bucket(birth_date_str, today=None):
    """Compute an athlete's age bucket from BirthDate string.

    Accepts 'YYYY-MM-DD', 'MM-YYYY', 'MM/DD/YYYY' formats — same as the
    parse_birthdate helper in main.py. Returns one of: '12-14', '15-16',
    '17-18', '19+', or None if unparseable.
    """
    if not birth_date_str:
        return None
    import datetime as _dt
    import re as _re
    if today is None:
        today = _dt.date.today()

    year = None
    # Try ISO YYYY-MM-DD
    m = _re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", birth_date_str)
    if m:
        year = int(m.group(1))
    if year is None:
        # MM-YYYY
        m = _re.match(r"^(\d{1,2})-(\d{4})$", birth_date_str)
        if m:
            year = int(m.group(2))
    if year is None:
        # MM/DD/YYYY
        m = _re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", birth_date_str)
        if m:
            year = int(m.group(3))
    if year is None:
        return None

    age = today.year - year
    if age < 12:
        return "11-"
    if age <= 14:
        return "12-14"
    if age <= 16:
        return "15-16"
    if age <= 18:
        return "17-18"
    return "19+"
