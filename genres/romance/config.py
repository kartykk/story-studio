"""
genres/romance/config.py — Romance genre constants.

Research sources:
- Romance Writers of America: 78% female readers, avg age 42
- HEA (Happily Ever After) mandatory — industry standard
- Bowlby attachment theory — romance satisfies attachment needs
- Black Moment positioning: 75-80% (validated by bestseller analysis)
"""

GENRE = "romance"
GENRE_DISPLAY = "Romance"

SUBGENRES = [
    "Contemporary",
    "Historical",
    "Paranormal",
    "Enemies-to-Lovers",
    "Second-Chance",
    "Forbidden Love",
]

RECOMMENDED_ARC_TYPES = ["Cinderella", "Man in Hole"]

CHAPTER_LENGTH_WORDS   = (2500, 3500)
SCENE_SEQUEL_RATIO     = 0.55            # more reflection than crime
HEA_REQUIRED           = True            # Happily Ever After — mandatory
MEET_POSITION          = 0.10           # leads must meet by 10%
FIRST_VULNERABILITY    = 0.25           # emotional crack in armor by 25%
BLACK_MOMENT_PCT       = 0.78           # relationship appears doomed at 78%
RESOLUTION_PCT         = 0.85
SEPARATION_MAX         = 2              # max times couple separates
THE_GROVEL_REQUIRED    = True           # hero must apologize if wrong

TARGET_EMOTIONS = {
    "joy":          0.75,
    "trust":        0.70,
    "anticipation": 0.70,
    "sadness":      0.45,    # during conflict/black moment
    "anger":        0.35,
    "fear":         0.20,
    "surprise":     0.40,
    "disgust":      0.10,
}

QUALITY_THRESHOLD = 72

READER_DEMOGRAPHICS = {
    "gender":          "78% female",
    "age_avg":         42,
    "reads_per_month": "46% read 4+ per month",
    "hea_requirement": "mandatory",
}

LOVE_LANGUAGE_WEIGHTS = {
    "words_of_affirmation": 0.25,
    "quality_time":         0.25,
    "acts_of_service":      0.20,
    "physical_touch":       0.20,
    "receiving_gifts":      0.10,
}

SUBGENRE_CONFIGS = {
    "Enemies-to-Lovers": {
        "forced_proximity_position": (0.20, 0.25),
        "vulnerability_reveal_position": 0.28,
        "hostility_beats": 3,
        "max_separations": 1,
    },
    "Second-Chance": {
        "remeet_position": (0.05, 0.15),
        "history_reveal_pct": 0.35,
        "forgiveness_arc": True,
        "both_must_change": True,
    },
    "Forbidden Love": {
        "external_antagonist": "the_prohibition_itself",
        "reactance_principle": True,
        "internal_conflict_ratio": 0.60,
    },
    "Historical": {
        "period_research_required": True,
        "period_constraints_as_obstacles": True,
        "chapter_length": (2500, 4000),
    },
    "Paranormal": {
        "world_building_required": True,
        "chapter_length": (2500, 3500),
    },
    "Contemporary": {
        "chapter_length": (2000, 3000),
        "modern_conflict_types": ["career vs love", "family pressure", "past trauma"],
    },
}
