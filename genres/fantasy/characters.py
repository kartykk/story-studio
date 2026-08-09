"""
genres/fantasy/characters.py — Fantasy character archetypes.
"""

CHOSEN_ONE_ARCHETYPE = {
    "vogler_archetype": "Hero",
    "jungian": "Hero (individuation journey)",
    "enneagram": "Type 6 (Loyalist) or Type 9 (Peacemaker) — transforms to Type 8",
    "mbti": "INFP or ENFP",
    "ocean": {"O": 0.8, "C": 0.5, "E": 0.5, "A": 0.8, "N": 0.6},
    "initial_state": "Ordinary, underestimated, outsider",
    "ghost_templates": [
        "Not belonging — hidden origin suppressed",
        "Loss of family/home that severed them from their past",
        "Being told they were ordinary/worthless when they weren't",
    ],
    "lie": "I am ordinary. I don't matter. There's nothing special about me.",
    "want": "To belong, to go home, to protect those I love",
    "need": "Accept destiny, step into power, become who you were meant to be",
    "speech_pattern": (
        "Earnest, questioning, self-deprecating at first. "
        "Grows more authoritative. Asks questions others take for granted."
    ),
    "arc": "Ordinary → Chosen → Tested → Broken → Reborn",
}

MENTOR_ARCHETYPE = {
    "vogler_archetype": "Mentor",
    "jungian": "Wise Old Man/Woman",
    "enneagram": "Type 5 (Investigator) or Type 1 (Reformer)",
    "flaws_required": ["Past failure", "Limited by own rules", "Blind spot about protagonist"],
    "departure_types": ["Death", "Sacrifice", "Revelation of limitation", "Necessary departure"],
    "gifts_to_hero": ["Knowledge", "Tools", "Confidence", "Permission to be who they are"],
    "speech_pattern": (
        "Cryptic, thoughtful, speaks in principles not instructions. "
        "Asks more than tells. Answers questions with better questions."
    ),
}

DARK_LORD_ARCHETYPE = {
    "vogler_archetype": "Shadow",
    "jungian": "Shadow (hero's dark side)",
    "psychology": "Represents what protagonist could become — mirror relationship",
    "motivation": "Ideological (believes they are right) — never random evil",
    "backstory": "Usually a fallen hero or corrupted idealist",
    "speech_pattern": "Calm authority. Certainty. Does not need to shout.",
}

ALLY_ARCHETYPE = {
    "vogler_archetype": "Ally",
    "function": "Found family — chosen bonds that replace lost family",
    "sub_types": ["Comic relief", "Warrior", "Scholar", "Healer", "Trickster"],
    "flaw_required": True,
    "rule": "Ally's flaw must create tension that tests and strengthens the bond",
}

SUGGESTED_CHARACTER_COUNT = {
    "tier1": 2,
    "tier2": 4,
    "tier3": 5,
}

CHARACTER_PSYCHOLOGY_GUIDE = {
    "tier1_roles": ["chosen_one", "dark_lord"],
    "tier2_roles": ["mentor", "ally_1", "ally_2", "love_interest"],
    "tier3_roles": ["threshold_guardian", "herald", "shapeshifter", "minor_villain", "citizen"],
}
