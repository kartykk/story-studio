"""
genres/literary/characters.py — Literary fiction character archetypes.
"""

COMPLEX_PROTAGONIST = {
    "vogler_archetype": "Hero (often subverted)",
    "enneagram": "Type 4 (Individualist) or Type 5 (Investigator)",
    "mbti": "INFJ, INTJ, or INFP",
    "ocean": {"O": 0.9, "C": 0.5, "E": 0.3, "A": 0.6, "N": 0.7},
    "ghost_templates": [
        "A childhood defined by a specific loss or silence",
        "A formative relationship that ended ambiguously",
        "A moment of moral failure they cannot undo",
        "Being seen incorrectly by everyone around them",
    ],
    "lie": "Varies by character — the lie must be specific, not archetypal",
    "need": "Self-understanding, not necessarily external change",
    "speech_pattern": (
        "Interior-heavy. What they say and what they mean diverge. "
        "Specific sensory observations that reveal emotional state. "
        "Often says less than they think."
    ),
    "arc_types": ["positive", "negative", "flat", "non-linear"],
    "rule": "Psychological authenticity is paramount. Contradictions must be believable.",
}

UNRELIABLE_NARRATOR = {
    "types": [
        "Self-deceived: sincerely believes their distorted version",
        "Naive: lacks knowledge to understand what they're describing",
        "Deliberate: knowingly omits or distorts",
        "Traumatized: distortion comes from psychological defense",
    ],
    "reader_contract": "Reader must be ABLE to detect the unreliability — not tricked unfairly",
    "mechanism": "Contradictions accumulate until the pattern is undeniable",
}

FOIL_CHARACTER = {
    "vogler_archetype": "Shadow or Ally",
    "function": "Embodies the road not taken — shows protagonist's alternative self",
    "relationship": "Friend, sibling, or rival who shares origin but made different choices",
}

SUGGESTED_CHARACTER_COUNT = {
    "tier1": 1,   # literary can have single deep protagonist
    "tier2": 2,
    "tier3": 3,
}

CHARACTER_PSYCHOLOGY_GUIDE = {
    "tier1_roles": ["protagonist"],
    "tier2_roles": ["foil", "intimate"],
    "tier3_roles": ["social_world", "past_figure", "witness"],
    "note": "Literary fiction often works with fewer, deeper characters rather than many shallow ones",
}
