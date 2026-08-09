"""
genres/crime/config.py — Crime genre constants.

Research sources:
- Reader demographics: 66% female, median age 55 (Nielsen BookScan 2023)
- Red herring timing: most effective just before reveal (Agatha Christie analysis)
- Cliffhanger endings: 80% of chapters in bestselling crime novels
- Inciting incident: before 10% (crime must happen early — reader commitment)
- Brewer & Lichtenstein suspense weights (crime-tuned)
"""

GENRE = "crime"
GENRE_DISPLAY = "Crime"

SUBGENRES = [
    "Noir",
    "Police Procedural",
    "Psychological Thriller",
    "Heist",
    "Legal Thriller",
    "Cozy Mystery",
]

RECOMMENDED_ARC_TYPES = ["Man in Hole", "Icarus", "Oedipus"]

CHAPTER_LENGTH_WORDS   = (1500, 2500)    # fast pacing — thriller standard
SCENE_SEQUEL_RATIO     = 0.70            # 70% action / 30% reflection (Swain)
MAX_CONSECUTIVE_HIGH_SIS = 2             # anti-monotony
INCITING_INCIDENT_PCT  = 0.08           # crime committed before 10%
DARK_VALLEY_PCT        = 0.75
REVEAL_PCT             = 0.80            # culprit reveal at 80%
RED_HERRING_COUNT      = (3, 5)          # 3-5 red herrings per story
CLIFFHANGER_RATE       = 0.80           # 80% of chapters end with hook

TARGET_EMOTIONS = {
    "anticipation": 0.75,   # suspense — primary
    "fear":         0.65,
    "anger":        0.45,
    "surprise":     0.60,
    "sadness":      0.30,
    "trust":        0.20,
    "joy":          0.15,
    "disgust":      0.35,
}

QUALITY_THRESHOLD = 68

READER_DEMOGRAPHICS = {
    "gender":          "66% female",
    "age_median":      55,
    "sensation_seeking": "high",
    "reads_per_month": 2.4,
}

# Brewer & Lichtenstein suspense weights (crime-tuned)
SUSPENSE_WEIGHTS = {
    "imminence":       0.35,
    "importance":      0.30,
    "foregroundedness": 0.25,
    "confidence":      0.10,
}

SUBGENRE_CONFIGS = {
    "Noir": {
        "emotional_tone": "dark, cynical, fatalistic",
        "protagonist_type": "anti-hero",
        "arc_types": ["Tragedy", "Oedipus"],
        "resolution": "ambiguous or negative",
        "chapter_length": (1500, 2200),
    },
    "Police Procedural": {
        "investigation_beats": 5,
        "pressure_valve_scenes": True,     # personal life scenes release tension
        "multiple_investigation_threads": True,
        "chapter_length": (1800, 2500),
    },
    "Psychological Thriller": {
        "unreliable_narrator": True,
        "midpoint_twist": True,
        "reader_complicity": True,
        "chapter_length": (1500, 2500),
    },
    "Heist": {
        "planning_phase_pct": (0.20, 0.45),
        "team_size": (4, 6),
        "twist_count": (2, 3),
        "chapter_length": (1800, 2500),
    },
    "Cozy Mystery": {
        "chapter_length": (1500, 2000),
        "violence_level": "off_page",
        "protagonist_type": "amateur_sleuth",
    },
    "Legal Thriller": {
        "courtroom_scenes": True,
        "chapter_length": (1800, 2500),
        "procedural_accuracy": True,
    },
}
