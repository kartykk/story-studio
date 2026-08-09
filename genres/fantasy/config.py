"""
genres/fantasy/config.py — Fantasy genre constants.

Research:
- Bettelheim (1976): Uses of Enchantment — fairy tale psychology
- Campbell (1949): Hero with a Thousand Faces — monomyth
- Tolkien: "On Fairy-Stories" — subcreation and secondary world
- Chosen One: wish fulfillment + significance need (Maslow)
- Mentor departure: forced individuation (Jungian)
"""

GENRE = "fantasy"
GENRE_DISPLAY = "Fantasy"

SUBGENRES = [
    "High Fantasy",
    "Dark Fantasy",
    "Urban Fantasy",
    "Grimdark",
    "Cozy Fantasy",
]

RECOMMENDED_ARC_TYPES = ["Rags to Riches", "Cinderella", "Man in Hole"]

CHAPTER_LENGTH_WORDS   = (4000, 8000)
SCENE_SEQUEL_RATIO     = 0.60
WORLDBUILDING_STRATEGY = "reveal_as_needed"
CHOSEN_ONE_REVEAL_PCT  = 0.12
MENTOR_DEPARTURE_REQUIRED = True
MENTOR_DEPARTURE_PCT   = (0.45, 0.60)
MAGIC_FIRST_REVEAL_PCT = 0.08
FRONT_LOADING_FORBIDDEN = True    # no info dumps before emotional investment

TARGET_EMOTIONS = {
    "anticipation": 0.80,
    "joy":          0.60,
    "fear":         0.50,
    "trust":        0.65,
    "surprise":     0.55,
    "sadness":      0.30,
    "anger":        0.35,
    "disgust":      0.15,
}

QUALITY_THRESHOLD = 70

JUNGIAN_ARCHETYPES_REQUIRED = ["Hero", "Mentor", "Shadow", "Ally"]

SUBGENRE_CONFIGS = {
    "High Fantasy": {
        "moral_clarity": "clear_good_vs_evil",
        "scope": "epic",
        "secondary_world": True,
        "chapter_length": (4000, 8000),
    },
    "Grimdark": {
        "moral_ambiguity": True,
        "consequences_realistic": True,
        "protagonist_type": "anti-hero",
        "reader_psychology": "eudaimonic",
        "chapter_length": (3000, 6000),
    },
    "Cozy Fantasy": {
        "stakes": "low",
        "tone": "warm, gentle, safe",
        "core_theme": "belonging, found family",
        "chapter_length": (2000, 3500),
    },
    "Urban Fantasy": {
        "setting": "real_world_with_magic",
        "worldbuilding_reduced": True,
        "chapter_length": (3000, 5000),
    },
    "Dark Fantasy": {
        "moral_ambiguity": True,
        "horror_elements": True,
        "chapter_length": (3500, 6000),
    },
}
