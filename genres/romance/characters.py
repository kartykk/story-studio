"""
genres/romance/characters.py — Romance character archetypes.
"""

HERO_ARCHETYPES = {
    "alpha": {
        "enneagram":  "Type 8 (Challenger)",
        "mbti":       "ENTJ or ESTJ",
        "ocean":      {"O": 0.5, "C": 0.8, "E": 0.8, "A": 0.3, "N": 0.4},
        "ghost_templates": [
            "Abandonment by someone they loved and trusted",
            "Betrayal that made them close themselves off",
            "Loss of control in a formative situation",
        ],
        "lie":  "Vulnerability = weakness. Love = losing control.",
        "need": "Learn to trust. Accept that vulnerability is strength.",
        "speech_pattern": (
            "Direct, commanding. Rarely asks — states. Short sentences. "
            "Uses actions not words. When emotional, goes silent or deflects."
        ),
        "arc": "Tamed by genuine love — not weakness, but chosen vulnerability",
    },
    "beta": {
        "enneagram":  "Type 2 (Helper) or Type 4 (Individualist)",
        "mbti":       "INFJ or ENFJ",
        "ocean":      {"O": 0.8, "C": 0.6, "E": 0.6, "A": 0.8, "N": 0.5},
        "ghost_templates": [
            "Not being enough — overlooked, undervalued",
            "Self-sacrifice that cost them their own happiness",
        ],
        "lie":  "I am not worthy of love unless I give everything",
        "need": "Learn self-worth is intrinsic, not earned through service",
        "speech_pattern": (
            "Warm, attentive, asks questions, notices emotional states. "
            "Listens more than talks. Says the right thing at the right time."
        ),
        "arc": "Learns to receive love, not just give it",
    },
}

HEROINE_ARCHETYPES = {
    "independent": {
        "enneagram":  "Type 1 (Reformer) or Type 3 (Achiever)",
        "ocean":      {"O": 0.7, "C": 0.8, "E": 0.7, "A": 0.5, "N": 0.5},
        "ghost_templates": [
            "Abandoned or had to be self-sufficient too young",
            "Career/independence came at cost of relationships",
        ],
        "lie":  "I don't need anyone. Dependence = vulnerability = hurt.",
        "need": "Allow someone in. Let love coexist with independence.",
        "speech_pattern": "Competent, occasionally sharp. Deflects with humor when vulnerable.",
    },
    "wounded": {
        "enneagram":  "Type 4 (Individualist) or Type 6 (Loyalist)",
        "ocean":      {"O": 0.8, "C": 0.6, "E": 0.4, "A": 0.7, "N": 0.7},
        "ghost_templates": [
            "Past relationship trauma or betrayal of trust",
            "Loss that made love feel dangerous",
        ],
        "lie":  "I am unlovable / All love ends in pain",
        "need": "Believe she deserves love. Trust again.",
        "speech_pattern": "Guarded, observant, occasionally self-deprecating. Opens up slowly.",
    },
}

SUGGESTED_CHARACTER_COUNT = {
    "tier1": 2,   # Hero + Heroine
    "tier2": 3,   # Best friend/confidant, family member, rival/obstacle
    "tier3": 3,   # Secondary social circle, minor antagonist
}

CHARACTER_PSYCHOLOGY_GUIDE = {
    "tier1_roles": ["hero", "heroine"],
    "tier2_roles": ["best_friend", "family", "rival"],
    "tier3_roles": ["coworker", "ex", "matchmaker"],
}
