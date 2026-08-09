"""
genres/literary/config.py — Literary fiction constants.

Research:
- Joyce: epiphany — "sudden spiritual manifestation"
- Kidd & Castano (2013): literary fiction improves Theory of Mind
- Mar et al. (2006): narrative transportation
- Subtext over explicit: showing inner life through action/object (Hemingway iceberg)
"""

GENRE = "literary"
GENRE_DISPLAY = "Literary Fiction"

SUBGENRES = [
    "Character Study",
    "Psychological",
    "Magical Realism",
    "Historical Literary",
    "Social Commentary",
]

RECOMMENDED_ARC_TYPES = ["Oedipus", "Icarus", "Man in Hole"]

CHAPTER_LENGTH_WORDS   = (3000, 5000)
SCENE_SEQUEL_RATIO     = 0.50
AMBIGUITY_ALLOWED      = True
EPIPHANY_REQUIRED      = True
EPIPHANY_PCT           = (0.70, 0.90)
NON_LINEAR_ALLOWED     = True
SUBTEXT_OVER_EXPLICIT  = True

TARGET_EMOTIONS = {
    "sadness":      0.50,
    "trust":        0.45,
    "joy":          0.40,
    "anticipation": 0.35,
    "surprise":     0.30,
    "fear":         0.25,
    "disgust":      0.20,
    "anger":        0.20,
}

QUALITY_THRESHOLD = 75     # highest bar — language is the experience

WRITING_STYLE_DIRECTIVES = {
    "language_as_aesthetic": True,
    "character_over_plot":   True,
    "inner_life_primary":    True,
    "resolution_ambiguity":  "allowed",
    "theme_density":         "high",
    "subtext_ratio":         "high",
}

SUBGENRE_CONFIGS = {
    "Character Study": {
        "plot_minimal": True,
        "interiority_maximum": True,
        "chapter_length": (3000, 6000),
    },
    "Psychological": {
        "unreliable_narrator": True,
        "interiority_maximum": True,
        "reveal_mechanism": "accumulation_of_contradictions",
    },
    "Magical Realism": {
        "magic_without_explanation": True,
        "magic_as_metaphor": True,
        "tone": "matter-of-fact about the impossible",
    },
    "Historical Literary": {
        "period_research_required": True,
        "period_as_theme": True,
        "chapter_length": (3500, 6000),
    },
    "Social Commentary": {
        "theme_explicit_allowed": True,
        "societal_critique": True,
    },
}
