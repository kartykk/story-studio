"""
genres/horror/config.py — Horror genre constants.

Research:
- Zillmann & Tamborini: Excitation Transfer Theory — fear converts to euphoria on resolution
- Three-stage fear model: dread (50-70% of buildup) → terror → horror
- False scare count: 3-7 (>7 = numbness; <3 = insufficient priming)
- Victim development window: first 10% before harm (reader must care to fear)
"""

GENRE = "horror"
GENRE_DISPLAY = "Horror"

SUBGENRES = [
    "Supernatural",
    "Psychological",
    "Body Horror",
    "Cosmic Horror",
    "Slasher",
    "Gothic",
]

RECOMMENDED_ARC_TYPES = ["Tragedy", "Oedipus"]

CHAPTER_LENGTH_WORDS   = (2000, 3000)
SCENE_SEQUEL_RATIO     = 0.62
DREAD_PHASE            = (0.0, 0.45)       # 50-70% of buildup = dread, no monster yet
FIRST_FALSE_SCARE_PCT  = 0.12             # cat scare before 15%
FALSE_SCARE_COUNT      = (3, 7)
MONSTER_PARTIAL_REVEAL = 0.45             # glimpse only
MONSTER_FULL_REVEAL    = 0.65
CLIMAX_PCT             = 0.85
VICTIM_DEVELOPMENT_PCT = 0.10             # humanize victims before horror strikes

TARGET_EMOTIONS = {
    "fear":         0.85,    # primary
    "anticipation": 0.75,    # dread before the scare
    "disgust":      0.50,
    "surprise":     0.55,
    "sadness":      0.35,
    "anger":        0.25,
    "joy":          0.05,
    "trust":        0.10,
}

QUALITY_THRESHOLD = 65

SUBGENRE_CONFIGS = {
    "Psychological": {
        "unreliable_narrator": True,
        "external_threat": False,
        "atmosphere": "paranoia, guilt, anxiety, madness",
        "resolution": "ambiguous",
    },
    "Cosmic Horror": {
        "knowledge_worsens_situation": True,
        "resolution": "no_resolution",
        "antagonist_motivation": "indifference",
        "explanation_forbidden": True,
    },
    "Body Horror": {
        "disgust_primary": True,
        "bodily_autonomy_violation": True,
        "abjection_principle": True,
    },
    "Gothic": {
        "setting_as_character": True,
        "decay_atmosphere": True,
        "isolation_required": True,
        "chapter_length": (2500, 4000),
    },
    "Supernatural": {
        "rules_for_entity": True,
        "chapter_length": (2000, 3000),
    },
    "Slasher": {
        "victim_count": (3, 8),
        "final_girl": True,
        "chapter_length": (1500, 2500),
    },
}
