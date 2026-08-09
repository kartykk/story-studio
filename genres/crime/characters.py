"""
genres/crime/characters.py — Crime character archetypes.

Research: Vogler (Hero's Journey), Enneagram typing for detective fiction,
OCEAN personality profiles validated against crime protagonist studies.
"""

DETECTIVE_ARCHETYPE = {
    "vogler_archetype":  "Hero",
    "enneagram_options": ["Type 1 (Reformer)", "Type 5 (Investigator)"],
    "mbti_options":      ["INTJ", "ISTJ", "INTP"],
    "ocean": {"O": 0.7, "C": 0.9, "E": 0.4, "A": 0.4, "N": 0.5},
    "ghost_templates": [
        "A past case where the wrong person was convicted",
        "Personal loss caused by a crime they couldn't prevent",
        "Being complicit in injustice while following orders",
        "A partner or mentor who died because of their failure",
    ],
    "lie_templates": [
        "I must solve everything alone — asking for help is weakness",
        "The system is corrupt — I can only trust myself",
        "If I work hard enough, I can undo past mistakes",
        "The truth always matters more than the consequences of finding it",
    ],
    "want":  "Solve the case, bring the criminal to justice",
    "need":  "Accept help / Find peace with imperfect justice / Trust again",
    "flaw_templates":     ["Obsessive", "Arrogant", "Isolated", "Ends-justify-means thinking"],
    "strength_templates": ["Relentless", "Perceptive", "Pattern recognition", "Analytical"],
    "speech_pattern": (
        "Terse, precise, observational. Asks questions that sound like statements. "
        "Never wastes words. Short declarative sentences. Notices things others miss — "
        "and mentions them obliquely."
    ),
    "sub_types": {
        "Empiricist (Holmes-type)": (
            "Physical evidence, sensory clues, experimental approach. "
            "Talks about facts, not feelings."
        ),
        "Psychologist (Poirot-type)": (
            "Human motives, behavioral psychology, deductive reasoning from character. "
            "Uses empathy as a tool, not a weakness."
        ),
    },
}

CRIMINAL_ARCHETYPE = {
    "vogler_archetype":  "Shadow",
    "enneagram_options": ["Type 3 (Achiever)", "Type 8 (Challenger)", "Type 6 (Loyalist, corrupted)"],
    "mbti_options":      ["ENTJ", "ESTJ", "INTJ"],
    "ocean": {"O": 0.5, "C": 0.7, "E": 0.6, "A": 0.2, "N": 0.6},
    "psychology_rule": "Must have sympathetic backstory — trauma or past injustice that humanizes",
    "ghost_templates": [
        "Wronged by the system they now exploit",
        "Desperate circumstances that corrupted good intentions",
        "Raised in an environment where crime was survival",
        "A powerful person who got away with injustice against them",
    ],
    "lie_templates": [
        "The system is rigged — I'm just playing by real rules",
        "I deserve what I take — the world owes me",
        "What I'm doing is justified by what was done to me",
        "I'm smarter than everyone — I'll never get caught",
    ],
    "reader_empathy_rule": "Reader should understand WHY even if they don't agree",
    "speech_pattern": (
        "Varies by type. Educated villains: precise, controlled, occasionally charming. "
        "Street villains: direct, threatening, economic with words. "
        "Corrupt officials: formal language masking corruption."
    ),
}

VICTIM_ARCHETYPE = {
    "vogler_archetype":   "Herald",   # their situation sets the story in motion
    "development_rule":   "Must be humanized BEFORE crime occurs — reader must care",
    "development_timing": "Establish in first 10% before harm occurs",
    "humanization_method": (
        "Show one specific dream, fear, or relationship. "
        "A single concrete detail does more than a paragraph of description."
    ),
}

CORRUPT_COP_ARCHETYPE = {
    "vogler_archetype":  "Shapeshifter",
    "enneagram_options": ["Type 3 (Achiever)", "Type 6 (Loyalist, fallen)"],
    "ghost_templates": [
        "Started with good intentions, made one small compromise",
        "Saw colleagues corrupt and chose survival over principle",
    ],
    "lie": "Everyone does this — I'm just being practical",
    "need": "Accountability. The truth will out.",
    "speech_pattern": (
        "Professionally smooth. Uses bureaucratic language to deflect. "
        "When cornered, becomes aggressive or emotional."
    ),
}

WITNESS_ARCHETYPE = {
    "vogler_archetype": "Threshold Guardian",
    "function": "Guards information the protagonist needs — either won't or can't share it",
    "motivation_options": ["Fear", "Loyalty", "Complicity", "Disbelief"],
}

# Character count recommendations
SUGGESTED_CHARACTER_COUNT = {
    "tier1": 2,   # Detective (protagonist) + Primary criminal (antagonist)
    "tier2": 3,   # Partner/ally, victim (if alive), key suspect
    "tier3": 5,   # Red herring suspects, minor witnesses, procedural contacts
}

# Psychological typing guide for character building
CHARACTER_PSYCHOLOGY_GUIDE = {
    "protagonist_archetype": "detective",
    "antagonist_archetype":  "criminal",
    "tier1_roles":  ["protagonist", "antagonist"],
    "tier2_roles":  ["partner", "victim", "key_suspect"],
    "tier3_roles":  ["red_herring_1", "red_herring_2", "witness", "authority_figure", "informant"],
}
