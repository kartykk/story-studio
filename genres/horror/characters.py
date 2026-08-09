"""
genres/horror/characters.py — Horror character archetypes.
"""

FINAL_GIRL_ARCHETYPE = {
    "vogler_archetype": "Hero",
    "enneagram": "Type 6 (Loyalist) or Type 1 (Reformer)",
    "mbti": "ISFJ or ISTJ",
    "traits": ["Intelligent", "Watchful", "Level-headed", "First to sense danger"],
    "ghost_templates": [
        "Overlooked or dismissed when they tried to warn others",
        "Survivor guilt from a past loss",
    ],
    "lie": "No one will believe me / I cannot survive this alone",
    "need": "Trust herself. Act on her instincts without external validation.",
    "arc": "Innocence/naivety → Empowerment through survival and determination",
    "modern_evolution": "Not punished for sexuality. Complex, well-rounded. Acts, not just reacts.",
    "speech_pattern": (
        "Observational, cautious. Voices concerns others dismiss. "
        "Asks the questions the group ignores. Specific about what feels wrong."
    ),
}

MONSTER_ARCHETYPE = {
    "vogler_archetype": "Shadow",
    "motivation_required": True,
    "unpredictability": "moderate",
    "psychology_depth_required": True,
    "sub_types": {
        "Intellectual Monster (Hannibal-type)": "High cognition, low emotion — calculating, cold",
        "Primal Monster": "High emotion, low cognition — rage, instinct, hunger",
        "Sympathetic Monster (Frankenstein-type)": "Tragic backstory, comprehensible motivation",
        "Indifferent Monster (Cosmic)": "No motivation — pure alien indifference",
    },
    "rule": "Purpose-driven evil > random evil. Reader fears what they understand.",
}

VICTIM_ARCHETYPE = {
    "vogler_archetype": "Herald",
    "development_timing": "First 10% — before any horror occurs",
    "empathy_mechanism": "Vulnerability reveal — specific fears, relationships, dreams",
    "rule": "Reader must care about them before they are harmed. One specific detail = more than pages of description.",
}

SKEPTIC_ARCHETYPE = {
    "vogler_archetype": "Threshold Guardian",
    "function": "Dismisses protagonist's warnings — creates isolation and raises stakes",
    "evolution": "Either converts to believer or dies as consequence of disbelief",
}

SUGGESTED_CHARACTER_COUNT = {
    "tier1": 2,
    "tier2": 3,
    "tier3": 4,
}

CHARACTER_PSYCHOLOGY_GUIDE = {
    "tier1_roles": ["final_girl", "monster"],
    "tier2_roles": ["skeptic", "victim_1", "ally"],
    "tier3_roles": ["victim_2", "victim_3", "authority_figure", "red_herring"],
}
