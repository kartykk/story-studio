"""
arc_calculator.py — Emotional arc curves and chapter intensity targets.

Research foundation:
- Reagan et al. (2016): 6 emotional arc shapes from 1,737 novels
- Save the Cat 15 beats with exact percentage positions
- Emotional intensity curve: baseline → spike@10% → dark valley@75% → climax@85%
"""

import math

from core.story_bible import BEAT_NAMES

# ── Reagan Arc Types ──────────────────────────────────────────────────────────

REAGAN_ARC_TYPES = [
    "Rags to Riches",   # steady rise
    "Tragedy",          # steady fall
    "Man in Hole",      # fall then rise
    "Icarus",           # rise then fall
    "Cinderella",       # rise-fall-rise
    "Oedipus",          # fall-rise-fall
]

ARC_DESCRIPTIONS = {
    "Rags to Riches":  "Steady emotional rise from low to high. Hope building throughout.",
    "Tragedy":         "Steady emotional fall from high to low. Fatalistic, dark, cynical.",
    "Man in Hole":     "Character falls into trouble then recovers. Most commercially successful arc.",
    "Icarus":          "Character rises then falls. Hubris, overreach, cautionary tale.",
    "Cinderella":      "Rise, fall, then triumphant rise. Romance, hope, earned happiness.",
    "Oedipus":         "Fall, partial recovery, final fall. Complex, literary, tragic.",
}

# Genre → recommended arc types (ordered by best fit)
GENRE_ARC_SUGGESTIONS = {
    "crime":    ["Man in Hole", "Icarus", "Oedipus"],
    "romance":  ["Cinderella", "Man in Hole"],
    "horror":   ["Tragedy", "Oedipus"],
    "fantasy":  ["Rags to Riches", "Cinderella", "Man in Hole"],
    "literary": ["Oedipus", "Icarus", "Man in Hole"],
}

# ── Save the Cat Beat Overlay ─────────────────────────────────────────────────
# (position_pct, emotional_intensity_modifier 0-1)
STC_BEAT_POSITIONS = {
    "Opening Image":     (0.01,  0.30),
    "Theme Stated":      (0.05,  0.35),
    "Set-Up":            (0.10,  0.50),
    "Catalyst":          (0.12,  0.72),   # inciting incident — spike
    "Debate":            (0.17,  0.42),
    "Break into Two":    (0.25,  0.58),
    "B Story":           (0.28,  0.38),
    "Fun and Games":     (0.40,  0.52),
    "Midpoint":          (0.50,  0.70),   # mid-story spike
    "Bad Guys Close In": (0.62,  0.62),
    "All Is Lost":       (0.75,  0.90),   # dark valley — near peak
    "Dark Night":        (0.78,  0.85),
    "Break into Three":  (0.82,  0.70),
    "Finale":            (0.88,  1.00),   # absolute climax
    "Final Image":       (0.99,  0.22),   # denouement
}

# Beat importance weights for Scene Interest Score
STC_BEAT_WEIGHTS = {
    "Opening Image":     40,
    "Theme Stated":      35,
    "Set-Up":            30,
    "Catalyst":          75,
    "Debate":            45,
    "Break into Two":    60,
    "B Story":           40,
    "Fun and Games":     50,
    "Midpoint":          80,
    "Bad Guys Close In": 65,
    "All Is Lost":       90,
    "Dark Night":        85,
    "Break into Three":  70,
    "Finale":            100,
    "Final Image":       45,
    "transition":        20,
    "default":           50,
}

# Map beat numbers and alternate spellings → canonical STC keys above
BEAT_NUMBER_TO_NAME = {num: name for num, name, _act in BEAT_NAMES}

BEAT_ALIASES = {
    "dark night of soul":       "Dark Night",
    "dark night of the soul":   "Dark Night",
    "dark night":               "Dark Night",
    "bad guys close in":        "Bad Guys Close In",
    "break into two":           "Break into Two",
    "break into three":         "Break into Three",
    "fun and games":            "Fun and Games",
    "b story":                  "B Story",
    "opening image":            "Opening Image",
    "theme stated":             "Theme Stated",
    "set-up":                   "Set-Up",
    "set up":                   "Set-Up",
    "all is lost":              "All Is Lost",
    "final image":              "Final Image",
}


def normalize_beat_name(name: str) -> str:
    """Map alternate beat labels to canonical STC_BEAT_WEIGHTS keys."""
    if not name:
        return name
    if name in STC_BEAT_WEIGHTS:
        return name
    key = name.lower().strip()
    if key in BEAT_ALIASES:
        return BEAT_ALIASES[key]
    for alias, canonical in BEAT_ALIASES.items():
        if alias in key or key in alias:
            return canonical
    return name


def normalize_beats_covered(beats_covered: list) -> list[str]:
    """Normalize beat numbers, strings, and aliases to canonical beat names."""
    result: list[str] = []
    for b in beats_covered or []:
        if isinstance(b, int) or (isinstance(b, str) and str(b).strip().isdigit()):
            n = int(b)
            raw = BEAT_NUMBER_TO_NAME.get(n, f"Beat {n}")
            result.append(normalize_beat_name(raw))
        else:
            result.append(normalize_beat_name(str(b).strip()))
    return result


# ── Arc Shape Functions ───────────────────────────────────────────────────────

def _rags_to_riches(p: float) -> float:
    return p

def _tragedy(p: float) -> float:
    return 1.0 - p

def _man_in_hole(p: float) -> float:
    # Fall to 0.2 at midpoint, then rise back up
    if p <= 0.5:
        return 0.8 - (0.6 * p)   # 0.8 → 0.5
    else:
        return 0.2 + (0.8 * (p - 0.5))  # 0.2 → 0.6

def _icarus(p: float) -> float:
    # Rise to peak at 60%, then fall
    if p <= 0.6:
        return p / 0.6
    else:
        return 1.0 - ((p - 0.6) / 0.4)

def _cinderella(p: float) -> float:
    # Rise to 0.4, dip to 0.2, rise to 1.0
    if p <= 0.35:
        return p / 0.35 * 0.7
    elif p <= 0.55:
        return 0.7 - ((p - 0.35) / 0.20 * 0.5)
    else:
        return 0.2 + ((p - 0.55) / 0.45 * 0.8)

def _oedipus(p: float) -> float:
    # Fall, partial rise, final fall
    if p <= 0.35:
        return 0.8 - (p / 0.35 * 0.5)
    elif p <= 0.65:
        return 0.3 + ((p - 0.35) / 0.30 * 0.5)
    else:
        return 0.8 - ((p - 0.65) / 0.35 * 0.7)

ARC_FUNCTIONS = {
    "Rags to Riches": _rags_to_riches,
    "Tragedy":        _tragedy,
    "Man in Hole":    _man_in_hole,
    "Icarus":         _icarus,
    "Cinderella":     _cinderella,
    "Oedipus":        _oedipus,
}


# ── STC Beat Overlay ──────────────────────────────────────────────────────────

def _stc_overlay(position_pct: float) -> float:
    """
    Return a 0-1 modifier based on proximity to Save the Cat beats.
    Beats pull intensity toward their target intensity at that position.
    """
    closest_dist = 1.0
    closest_modifier = 0.5

    for beat_name, (beat_pos, beat_intensity) in STC_BEAT_POSITIONS.items():
        dist = abs(position_pct - beat_pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_modifier = beat_intensity

    # Weight: if within 3% of a beat, use mostly the beat's intensity
    if closest_dist <= 0.03:
        return closest_modifier
    # Otherwise blend: 70% arc shape, 30% nearest beat
    return None   # signal to use arc shape only


# ── Public API ────────────────────────────────────────────────────────────────

def get_target_intensity(position_pct: float, arc_type: str) -> float:
    """
    Returns target emotion intensity (0.0-1.0) for a chapter at position_pct.
    Blends Reagan arc shape with Save the Cat beat overlay.

    Args:
        position_pct: 0.0-1.0 (chapter's position in story)
        arc_type: one of REAGAN_ARC_TYPES

    Returns:
        float: target intensity 0.0-1.0
    """
    position_pct = max(0.0, min(1.0, position_pct))

    arc_fn = ARC_FUNCTIONS.get(arc_type, _man_in_hole)
    arc_intensity = arc_fn(position_pct)

    stc = _stc_overlay(position_pct)
    if stc is not None:
        # Near a major beat — blend 60% beat, 40% arc
        return round(0.60 * stc + 0.40 * arc_intensity, 3)
    else:
        return round(arc_intensity, 3)


def assign_chapter_intensities(
    chapter_count: int,
    arc_type: str,
    beats_per_chapter: list[list[str]] = None,
) -> list[float]:
    """
    Compute target_emotion_intensity for each chapter.

    Args:
        chapter_count: total number of chapters
        arc_type: one of REAGAN_ARC_TYPES
        beats_per_chapter: optional list of beat name lists, one per chapter

    Returns:
        list[float]: intensity 0.0-1.0 per chapter (length = chapter_count)
    """
    intensities = []
    for i in range(chapter_count):
        # Chapter position = midpoint of chapter span
        position = (i + 0.5) / chapter_count

        # If we know which STC beats this chapter covers, use the highest-weight beat
        if beats_per_chapter and i < len(beats_per_chapter):
            chapter_beats = normalize_beats_covered(beats_per_chapter[i])
            if chapter_beats:
                best_beat = max(chapter_beats, key=lambda b: STC_BEAT_WEIGHTS.get(b, 50))
                best_pos, best_intensity = STC_BEAT_POSITIONS.get(best_beat, (position, 0.5))
                # Blend: 70% beat intensity, 30% arc at position
                arc_fn = ARC_FUNCTIONS.get(arc_type, _man_in_hole)
                blended = 0.70 * best_intensity + 0.30 * arc_fn(position)
                intensities.append(round(blended, 3))
                continue

        intensities.append(get_target_intensity(position, arc_type))

    return intensities


def suggest_arc_type(genre: str, tone: str = "") -> list[str]:
    """
    Return arc types ordered by fit for the given genre/tone.

    Args:
        genre: story genre (crime, romance, horror, fantasy, literary)
        tone: optional tone modifier (dark, light, epic, etc.)

    Returns:
        list[str]: arc types ordered by recommendation
    """
    base = GENRE_ARC_SUGGESTIONS.get(genre.lower(), REAGAN_ARC_TYPES[:])

    # Tone overrides
    tone_lower = tone.lower()
    if "dark" in tone_lower or "grim" in tone_lower:
        # Push tragic arcs to front
        tragic = ["Tragedy", "Oedipus"]
        base = tragic + [a for a in base if a not in tragic]
    elif "light" in tone_lower or "hopeful" in tone_lower or "uplifting" in tone_lower:
        # Push positive arcs to front
        positive = ["Rags to Riches", "Cinderella"]
        base = positive + [a for a in base if a not in positive]

    return base


def get_arc_description(arc_type: str) -> str:
    return ARC_DESCRIPTIONS.get(arc_type, "")


def beat_weight(beat_name: str) -> int:
    """Return the Scene Interest Score weight for a beat name."""
    return STC_BEAT_WEIGHTS.get(beat_name, STC_BEAT_WEIGHTS["default"])
